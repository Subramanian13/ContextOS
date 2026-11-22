import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../lib/api'
import { onProjectInvalidated } from '../lib/projectState'
import type { ProjectDetail, Schedule } from '../types'

export function useProjectData(id: string, viewKey = '') {
  const [state, setState] = useState<{ project?: ProjectDetail; schedule?: Schedule; error?: string; loading: boolean }>({ loading: true })
  const generation=useRef(0)
  const load = useCallback(() => {
    const requestGeneration=++generation.current
    setState({ loading: true })
    Promise.all([api.project(id), api.schedule(id)])
      .then(([project, schedule]) => {if(requestGeneration===generation.current)setState({ project, schedule, loading: false })})
      .catch((error: Error) => {if(requestGeneration===generation.current)setState({ error: error.message, loading: false })})
  },[id])
  useEffect(()=>{load()}, [load,viewKey])
  useEffect(()=>onProjectInvalidated(projectId=>{if(projectId===id)load()}),[id,load])
  return { ...state, reload: load }
}
