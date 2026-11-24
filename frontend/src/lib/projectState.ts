const PROJECT_INVALIDATED = 'contextos:project-invalidated'

export function invalidateProject(projectId: string) {
  window.dispatchEvent(new CustomEvent(PROJECT_INVALIDATED, {detail:{projectId}}))
}

export function onProjectInvalidated(listener: (projectId:string)=>void) {
  const handler=(event:Event)=>listener((event as CustomEvent<{projectId:string}>).detail.projectId)
  window.addEventListener(PROJECT_INVALIDATED,handler)
  return ()=>window.removeEventListener(PROJECT_INVALIDATED,handler)
}
