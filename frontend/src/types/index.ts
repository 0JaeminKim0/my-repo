// Tool Types
export interface ToolParameter {
  name: string
  type: 'string' | 'integer' | 'number' | 'boolean' | 'array' | 'object'
  description: string
  required: boolean
  default?: any
}

export interface Tool {
  tool_id: string
  version: string
  name: string
  description: string
  category: string
  input_schema: ToolParameter[]
  output_schema: ToolParameter[]
  has_prompt: boolean
}

// Workflow Types
export interface ConstantMapping {
  type: 'constant'
  value: any
}

export interface FromNodeMapping {
  type: 'fromNode'
  node_id: string
  path: string
}

export type InputMapping = ConstantMapping | FromNodeMapping

export interface NodePrompt {
  system: string
  user: string
  force_json: boolean
}

export interface WorkflowNode {
  node_id: string
  tool_id: string
  version: string
  input_mapping: Record<string, InputMapping>
  prompt?: NodePrompt
}

export interface FinalOutputMapping {
  node_id: string
  path: string
}

export interface FinalOutput {
  schema: {
    type: string
    required: string[]
    properties: Record<string, any>
  }
  mapping: Record<string, FinalOutputMapping>
}

export interface Workflow {
  workflow_id: string
  project_id: string
  name: string
  description: string
  nodes: WorkflowNode[]
  final_output?: FinalOutput
  created_at: string
  updated_at: string
}

// Run Types
export type RunStatus = 'PENDING' | 'RUNNING' | 'SUCCESS' | 'FAILED'
export type NodeTraceStatus = 'PENDING' | 'RUNNING' | 'SUCCESS' | 'FAILED' | 'SKIPPED'

export interface NodeTraceError {
  code: string
  message: string
  details: Record<string, any>
}

export interface NodeTrace {
  node_id: string
  tool_id: string
  status: NodeTraceStatus
  started_at?: string
  ended_at?: string
  input_summary: Record<string, any>
  output_summary: Record<string, any>
  error?: NodeTraceError
}

export interface RunCost {
  tokens: number
  prompt_tokens: number
  completion_tokens: number
}

export interface RunMeta {
  started_at?: string
  ended_at?: string
  status: RunStatus
  cost: RunCost
}

export interface Run {
  run_id: string
  workflow_id: string
  status: RunStatus
  trace: NodeTrace[]
  node_outputs: Record<string, any>
  final_output?: Record<string, any>
  error?: NodeTraceError
  meta: RunMeta
  created_at: string
}
