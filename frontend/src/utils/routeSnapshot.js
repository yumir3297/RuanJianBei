export function routeSnapshot(route, existingConstraints = {}) {
  const routeId = route.routeId || route.id;
  return {
    constraints: { available_minutes: null, interests: [], companions: [], required_spots: [], excluded_spots: [], walking_preference: null, ...existingConstraints },
    stops: (route.spots || []).slice(0, 50).map(name => ({ name, spot_id: null, resolved: false })),
    source: route.routeId ? 'recommendation' : 'preset',
    source_references: routeId ? [{ source_type: route.routeId ? 'recommendation' : 'preset_route', source_id: String(routeId), label: route.title || '' }] : [],
  };
}
