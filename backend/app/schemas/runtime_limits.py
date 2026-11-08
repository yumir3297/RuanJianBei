from pydantic import BaseModel, ConfigDict, Field


class KnowledgeImportLimits(BaseModel):
    model_config = ConfigDict(extra="forbid")
    max_files: int = Field(ge=1)
    max_file_bytes: int = Field(ge=1)


class DisplayAssetLimits(BaseModel):
    model_config = ConfigDict(extra="forbid")
    max_image_bytes: int = Field(ge=1)


class AdminRuntimeLimits(BaseModel):
    model_config = ConfigDict(extra="forbid")
    knowledge_import: KnowledgeImportLimits
    display_assets: DisplayAssetLimits
