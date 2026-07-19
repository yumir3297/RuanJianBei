"""Debug: see what's at column 788 in the Coze response"""
import asyncio, sys, os, json, httpx
sys.path.insert(0, "d:/桌面/软件杯/backend")
os.chdir("d:/桌面/软件杯/backend")

async def main():
    from app.core.config import get_settings
    settings = get_settings()
    from app.db.session import AsyncSessionLocal
    from app.repositories.knowledge import KnowledgeRepository
    from app.repositories.route import RouteRepository
    from app.services.live_data.service import LiveDataService

    async with AsyncSessionLocal() as session:
        kr = KnowledgeRepository(session)
        rr = RouteRepository(session)
        attractions = await kr.list_by_category("景点信息")
        routes = await rr.list_all()

    live_svc = LiveDataService(settings)
    live_ctx = live_svc.build_context(attractions)

    # Same payload as pipeline._build_route_candidates
    def _extract_route_stops(route_plan, attractions):
        stops = []
        for a in attractions:
            aliases = [item.strip() for item in a.aliases.split("|") if item.strip()]
            terms = [a.title, *aliases]
            if any(term and term in route_plan for term in terms):
                stops.append({"attraction_id": str(a.id), "name": a.title})
        return stops

    payload = {
        "question": "帮我推荐灵山游览路线，避开人流",
        "visitor_profile_json": json.dumps({
            "audience_type": None, "available_hours": None,
            "avoid_crowded": None, "interests": [],
            "active_subject": None, "input_mode": "text",
        }, ensure_ascii=False),
        "route_candidates_json": json.dumps({
            "routes": [{
                "id": r.id, "name": r.title,
                "duration": r.duration_label,
                "route_plan": r.route_plan,
                "stops": _extract_route_stops(r.route_plan, attractions),
            } for r in routes]
        }, ensure_ascii=False),
        "live_context_json": json.dumps(
            live_ctx.model_dump(mode="json"), ensure_ascii=False
        ),
        "allowed_attraction_ids_json": json.dumps(
            [str(a.id) for a in attractions], ensure_ascii=False
        ),
    }

    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(
            settings.coze_run_url,
            headers={
                "Authorization": f"Bearer {settings.coze_token}",
                "Content-Type": "application/json",
            },
            json=payload,
        )

    outer = r.json()
    inner = outer.get("result_json", "")
    
    # Show around column 788
    pos = 788
    print(f"Around char {pos}:")
    print(f"...{repr(inner[pos-30:pos+30])}...")
    print()
    
    # Try json5 or manual fix
    try:
        parsed = json.loads(inner)
        print("PARSE OK (shouldn't happen)")
    except json.JSONDecodeError as e:
        print(f"Error: {e}")
        # Show context
        start = max(0, e.pos - 80)
        end = min(len(inner), e.pos + 80)
        print(f"\nContext around error:\n{inner[start:end]}")
        print(f"\nChar at error pos: U+{ord(inner[e.pos]):04X} = {repr(inner[e.pos])}")

asyncio.run(main())
