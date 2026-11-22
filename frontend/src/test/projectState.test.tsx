import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { api } from '../lib/api'
import { invalidateProject } from '../lib/projectState'
import { useProjectData } from '../hooks/useProjectData'
import { project, schedule } from './fixtures'

afterEach(()=>vi.restoreAllMocks())

it('refreshes project and schedule after execution invalidation',async()=>{
  const updated={...project,version:2,tasks:project.tasks.map(task=>task.id==='build'?{...task,resource_id:'impl'}:task)}
  vi.spyOn(api,'project').mockResolvedValueOnce(project).mockResolvedValueOnce(updated)
  vi.spyOn(api,'schedule').mockResolvedValue(schedule)
  const {result}=renderHook(()=>useProjectData('acme-crm','recovery'))
  await waitFor(()=>expect(result.current.project?.version).toBe(1))
  act(()=>invalidateProject('acme-crm'))
  await waitFor(()=>expect(result.current.project?.version).toBe(2))
  expect(result.current.project?.tasks.find(task=>task.id==='build')?.resource_id).toBe('impl')
})

it('prevents an older in-flight response from overwriting newer project state',async()=>{
  let releaseOld:(value:typeof project)=>void=()=>undefined
  const old=new Promise<typeof project>(resolve=>{releaseOld=resolve})
  const updated={...project,version:2}
  vi.spyOn(api,'project').mockReturnValueOnce(old).mockResolvedValueOnce(updated)
  vi.spyOn(api,'schedule').mockResolvedValue(schedule)
  const {result}=renderHook(()=>useProjectData('acme-crm','overview'))
  act(()=>invalidateProject('acme-crm'))
  await waitFor(()=>expect(result.current.project?.version).toBe(2))
  await act(async()=>releaseOld(project))
  expect(result.current.project?.version).toBe(2)
})
