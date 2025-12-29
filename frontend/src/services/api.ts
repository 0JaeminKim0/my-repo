import axios from 'axios'
import type { Tool, Workflow, Run, WorkflowNode, FinalOutput } from '../types'

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json'
  }
})

// Tools API
export const toolsApi = {
  list: async (category?: string): Promise<{ tools: Tool[], total: number }> => {
    const params = category ? { category } : {}
    const { data } = await api.get('/tools', { params })
    return data
  },
  
  get: async (toolId: string, version?: string): Promise<Tool> => {
    const params = version ? { version } : {}
    const { data } = await api.get(`/tools/${toolId}`, { params })
    return data
  },
  
  getCategories: async (): Promise<{ categories: string[] }> => {
    const { data } = await api.get('/tools/categories')
    return data
  }
}

// Workflows API
export const workflowsApi = {
  list: async (projectId?: string): Promise<{ workflows: Workflow[], total: number }> => {
    const params = projectId ? { project_id: projectId } : {}
    const { data } = await api.get('/workflows', { params })
    return data
  },
  
  get: async (workflowId: string): Promise<Workflow> => {
    const { data } = await api.get(`/workflows/${workflowId}`)
    return data
  },
  
  create: async (workflow: {
    name: string
    description?: string
    project_id?: string
    nodes: WorkflowNode[]
    final_output?: FinalOutput
  }): Promise<Workflow> => {
    const { data } = await api.post('/workflows', workflow)
    return data
  },
  
  update: async (workflowId: string, workflow: Partial<{
    name: string
    description: string
    nodes: WorkflowNode[]
    final_output: FinalOutput
  }>): Promise<Workflow> => {
    const { data } = await api.put(`/workflows/${workflowId}`, workflow)
    return data
  },
  
  delete: async (workflowId: string): Promise<void> => {
    await api.delete(`/workflows/${workflowId}`)
  }
}

// Runs API
export const runsApi = {
  list: async (workflowId?: string, status?: string): Promise<{ runs: Run[], total: number }> => {
    const params: Record<string, string> = {}
    if (workflowId) params.workflow_id = workflowId
    if (status) params.status = status
    const { data } = await api.get('/runs', { params })
    return data
  },
  
  get: async (runId: string): Promise<Run> => {
    const { data } = await api.get(`/runs/${runId}`)
    return data
  },
  
  create: async (workflowId: string, draft?: Record<string, any>): Promise<Run> => {
    const { data } = await api.post('/runs', { workflow_id: workflowId, draft })
    return data
  },
  
  delete: async (runId: string): Promise<void> => {
    await api.delete(`/runs/${runId}`)
  }
}

// Files API
export const filesApi = {
  upload: async (file: File): Promise<{ file_ref: string, filename: string, size: number, content_type: string }> => {
    const formData = new FormData()
    formData.append('file', file)
    const { data } = await api.post('/files/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    return data
  },
  
  get: async (fileRef: string): Promise<{ file_ref: string, filename: string, size: number, content_type: string }> => {
    const { data } = await api.get(`/files/${fileRef}`)
    return data
  },
  
  delete: async (fileRef: string): Promise<void> => {
    await api.delete(`/files/${fileRef}`)
  }
}

export default api
