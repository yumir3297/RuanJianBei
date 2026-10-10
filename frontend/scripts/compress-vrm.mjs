/**
 * VRM 资产压缩管线（项目可复用工具）。
 *
 * 用法：
 *   node scripts/compress-vrm.mjs <输入.vrm/.glb> <输出.glb>
 *   node scripts/compress-vrm.mjs <输入目录> <输出目录>   （批量处理目录内全部 .vrm/.glb）
 *
 * 为什么要自定义脚本而不是直接用 gltf-transform CLI：
 * 1. CLI 不认识 .vrm 扩展名，会输出 .gltf JSON 文本而非二进制 GLB；
 * 2. CLI 未注册 VRMC_vrm / VRMC_springBone / VRMC_materials_mtoon 扩展，
 *    读取时这些扩展会被整体丢弃（reader 对未注册扩展仅告警），
 *    模型将失去人形骨骼映射、弹簧骨骼物理与 MToon 卡通材质。
 *
 * 本脚本通过「直通扩展（passthrough extension）」原样保留 VRMC_* 的 JSON：
 * - 根级扩展（VRMC_vrm / VRMC_springBone 等）在 read 时捕获、write 时写回；
 * - 逐材质扩展（VRMC_materials_mtoon）按材质索引捕获，写回阶段重新注入。
 *
 * 压缩变换只使用不改变节点/材质/网格索引顺序的步骤（textureCompress + meshopt），
 * 因此 VRMC_* 原始 JSON 中的索引引用在压缩后依然有效。
 *
 * 压缩产物依赖：
 * - EXT_meshopt_compression + KHR_mesh_quantization：three.js GLTFLoader 需 setMeshoptDecoder；
 * - EXT_texture_webp：three.js GLTFLoader 原生支持（现代浏览器均支持 WebP）。
 *
 * 索引修复（重要）：gltf-transform 的 writer 只为「被材质引用」的纹理生成 textures 定义，
 * 仅被 VRMC_* 扩展引用的纹理（如 MToon 的描边贴图、UV 动画遮罩、缩略图）会失去定义，
 * 浏览器端 MToon 材质按越界下标取 textures[j] 得到 undefined，直接抛错导致模型加载失败。
 * 因此在 write() 阶段：先按 EXT_texture_webp.source（= 原纹理索引）反查每个纹理的新下标，
 * 为被 writer 丢弃的纹理按相同结构补建定义，再重映射直通扩展 JSON 里的全部纹理引用。
 */

import fs from "node:fs";
import path from "node:path";
import { Extension, NodeIO } from "@gltf-transform/core";
import { ALL_EXTENSIONS } from "@gltf-transform/extensions";
import { meshopt, textureCompress } from "@gltf-transform/functions";
import { MeshoptDecoder, MeshoptEncoder } from "meshoptimizer";
import sharp from "sharp";

/** VRM 1.0 规范中的根级扩展（按项目当前模型实际使用的为准，多列无副作用）。 */
const VRM_ROOT_EXTENSIONS = [
	"VRMC_vrm",
	"VRMC_springBone",
	"VRMC_vrm_animation",
	"VRMC_node_constraint",
	"VRMC_materials_hdri_emissiveStrength",
];

/** VRM 1.0 的逐材质扩展（MToon 卡通着色）。 */
const VRM_MATERIAL_EXTENSION = "VRMC_materials_mtoon";

/**
 * 创建一个「直通」扩展类：读取时原样捕获 VRMC_* JSON，写出时原样写回。
 * 根级与逐材质两种挂载点都处理，保证无论扩展定义在哪个层级都不丢。
 */
function createVrmPassthrough(extensionName) {
	return class VRMPassthroughExtension extends Extension {
		static EXTENSION_NAME = extensionName;
		extensionName = extensionName;

		/** 根级扩展 JSON（undefined 表示源文件根级没有该扩展）。 */
		rootJson;
		/** 逐材质扩展定义，按下标与 materials 数组对齐（null 表示该材质未挂载）。 */
		materialDefs = [];

		read(readerContext) {
			const json = readerContext.jsonDoc.json;
			this.rootJson = json.extensions?.[extensionName];
			this.materialDefs = (json.materials || []).map(
				(materialDef) => materialDef.extensions?.[extensionName] ?? null,
			);
			return this;
		}

		write(writerContext) {
			const json = writerContext.jsonDoc.json;
			// extension.write() 在 writer 组装完 json 的最后阶段被调用，此时可以安全回填。
			// 但 json.textures 只包含被材质引用的纹理，需先补全定义、再重映射直通 JSON 里的纹理引用。
			const texMap = buildTextureIndexMap(json);
			if (this.rootJson !== undefined) {
				remapTextureReferences(this.rootJson, texMap);
				json.extensions = json.extensions || {};
				json.extensions[extensionName] = this.rootJson;
			}
			(json.materials || []).forEach((materialDef, index) => {
				const def = this.materialDefs[index];
				if (def === undefined || def === null) return;
				remapTextureReferences(def, texMap);
				materialDef.extensions = materialDef.extensions || {};
				materialDef.extensions[extensionName] = def;
			});
			return this;
		}
	};
}

/**
 * 构建「原纹理索引 -> 输出 textures 数组下标」映射，并补全被 writer 丢弃的纹理定义。
 *
 * 原理：
 * - writer 输出的 json.images 与原纹理一一对应（images[i] 即原纹理 i，顺序保持）；
 * - json.textures 只包含被材质引用的纹理，每个定义都带 EXT_texture_webp.source（= 原索引），
 *   据此可以反查每个原索引在输出 textures 里的新下标；
 * - 被丢弃的纹理总是最高索引（尾部），按相同结构补建并追加到尾部后，
 *   数组下标恰好与原索引一一对应。
 */
function buildTextureIndexMap(json) {
	const textures = (json.textures = json.textures || []);
	const useWebp =
		textures.some((def) => def?.extensions?.EXT_texture_webp) ||
		Boolean(json.extensionsUsed?.includes("EXT_texture_webp"));
	const texMap = new Map();
	textures.forEach((def, defIndex) => {
		const source = def?.extensions?.EXT_texture_webp?.source ?? def?.source;
		if (Number.isInteger(source)) texMap.set(source, defIndex);
	});
	const imageCount = (json.images || []).length;
	for (let originalIndex = 0; originalIndex < imageCount; originalIndex++) {
		if (texMap.has(originalIndex)) continue;
		texMap.set(originalIndex, textures.length);
		textures.push(
			useWebp
				? { sampler: 0, extensions: { EXT_texture_webp: { source: originalIndex } } }
				: { sampler: 0, source: originalIndex },
		);
	}
	return texMap;
}

/**
 * 递归重映射扩展 JSON 里的纹理引用。
 * VRMC 扩展中所有纹理槽位的键名都以 *Texture 结尾且形如 {index: N, ...}；
 * 其余 {index: N}（如表情 morph 的 index）不是纹理引用，必须按键名区分，
 * 否则会把表情/骨骼等非纹理索引错误改写。
 */
function remapTextureReferences(node, texMap) {
	if (Array.isArray(node)) {
		node.forEach((item) => remapTextureReferences(item, texMap));
		return;
	}
	if (node === null || typeof node !== "object") return;
	for (const [key, value] of Object.entries(node)) {
		if (
			/Texture$/.test(key) &&
			value && typeof value === "object" && !Array.isArray(value) &&
			Number.isInteger(value.index)
		) {
			const mapped = texMap.get(value.index);
			if (mapped === undefined) {
				throw new Error(`纹理引用越界且无法修复：${key}.index=${value.index}`);
			}
			value.index = mapped;
		} else {
			remapTextureReferences(value, texMap);
		}
	}
}

const PassthroughClasses = [...VRM_ROOT_EXTENSIONS, VRM_MATERIAL_EXTENSION].map(createVrmPassthrough);

async function compressFile(io, inputPath, outputPath, { textureSize, quality }) {
	const beforeBytes = fs.statSync(inputPath).size;
	const document = await io.read(inputPath);

	const stats = {
		images: document.getRoot().listTextures().length,
		nodes: document.getRoot().listNodes().length,
		materials: document.getRoot().listMaterials().length,
	};

	await document.transform(
		// 纹理：等比缩小到上限尺寸并转 WebP（关键体积来源；索引顺序不变）。
		textureCompress({
			encoder: sharp,
			targetFormat: "webp",
			resize: textureSize,
			quality,
		}),
		// 几何：量化 + meshopt 压缩（自动写入 EXT_meshopt_compression，且标记为 required）。
		meshopt({ encoder: MeshoptEncoder, level: "high" }),
	);

	await io.write(outputPath, document);
	const afterBytes = fs.statSync(outputPath).size;

	console.log(
		`✔ ${path.basename(inputPath)}: ${(beforeBytes / 1024 / 1024).toFixed(2)}MB -> ` +
			`${(afterBytes / 1024 / 1024).toFixed(2)}MB ` +
			`(保留 ${stats.images} 张纹理 / ${stats.nodes} 个节点 / ${stats.materials} 个材质)`,
	);
}

async function main() {
	await MeshoptEncoder.ready;

	const io = new NodeIO()
		.registerExtensions([...ALL_EXTENSIONS, ...PassthroughClasses])
		.registerDependencies({
			"meshopt.decoder": MeshoptDecoder,
			"meshopt.encoder": MeshoptEncoder,
		});

	const [, , inputArg, outputArg] = process.argv;
	if (!inputArg || !outputArg) {
		console.error("用法：node scripts/compress-vrm.mjs <输入.vrm|.glb|目录> <输出.glb|目录>");
		process.exit(1);
	}

	const options = { textureSize: [1024, 1024], quality: 85 };

	if (fs.statSync(inputArg).isDirectory()) {
		fs.mkdirSync(outputArg, { recursive: true });
		const entries = fs
			.readdirSync(inputArg)
			.filter((name) => /\.(vrm|glb)$/i.test(name));
		if (!entries.length) {
			console.error(`输入目录中没有 .vrm/.glb 文件：${inputArg}`);
			process.exit(1);
		}
		for (const name of entries) {
			const outName = `${path.basename(name, path.extname(name))}.glb`;
			await compressFile(io, path.join(inputArg, name), path.join(outputArg, outName), options);
		}
	} else {
		await compressFile(io, inputArg, outputArg, options);
	}
}

main().catch((error) => {
	console.error(error);
	process.exit(1);
});
