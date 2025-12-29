import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { toolsApi, workflowsApi, filesApi } from '../services/api'
import type { Tool, Workflow, WorkflowNode, InputMapping, NodePrompt } from '../types'

// PRD 8.1: Node Input 설정 UI
interface NodeEditorProps {
  node: WorkflowNode
  tool: Tool | null
  prevNodes: WorkflowNode[]
  prevOutputs: Record<string, Tool | null>
  onUpdate: (node: WorkflowNode) => void
  onRemove: () => void
}

function NodeEditor({ node, tool, prevNodes, prevOutputs, onUpdate, onRemove }: NodeEditorProps) {
  const [isExpanded, setIsExpanded] = useState(true)
  const [uploadingFile, setUploadingFile] = useState<string | null>(null)
  const [uploadedFiles, setUploadedFiles] = useState<Record<string, { file_ref: string; filename: string }>>({})

  const updateInputMapping = (paramName: string, mapping: InputMapping) => {
    const newMapping = { ...node.input_mapping, [paramName]: mapping }
    onUpdate({ ...node, input_mapping: newMapping })
  }

  const updatePrompt = (field: keyof NodePrompt, value: any) => {
    const newPrompt: NodePrompt = {
      system: node.prompt?.system || 'You are a helpful assistant.',
      user: node.prompt?.user || '',
      force_json: node.prompt?.force_json || false,
      [field]: value
    }
    onUpdate({ ...node, prompt: newPrompt })
  }

  // File upload handler
  const handleFileUpload = async (paramName: string, file: File) => {
    setUploadingFile(paramName)
    try {
      const result = await filesApi.upload(file)
      setUploadedFiles(prev => ({
        ...prev,
        [paramName]: { file_ref: result.file_ref, filename: result.filename }
      }))
      updateInputMapping(paramName, { type: 'constant', value: result.file_ref })
    } catch (error: any) {
      console.error('Failed to upload file:', error)
      alert(error.response?.data?.error?.message || 'Failed to upload file')
    } finally {
      setUploadingFile(null)
    }
  }

  // Check if parameter is a file reference
  const isFileRefParam = (paramName: string) => {
    return paramName.includes('file') || paramName === 'file_ref'
  }

  // Get available outputs from previous nodes
  const getAvailableOutputs = () => {
    const outputs: { nodeId: string; nodeName: string; path: string; type: string }[] = []
    
    prevNodes.forEach(prevNode => {
      const prevTool = prevOutputs[prevNode.node_id]
      if (prevTool) {
        prevTool.output_schema.forEach(output => {
          outputs.push({
            nodeId: prevNode.node_id,
            nodeName: prevNode.tool_id,
            path: output.name,
            type: output.type
          })
        })
      }
    })
    
    return outputs
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm mb-4">
      <div 
        className="flex items-center justify-between px-4 py-3 bg-gray-50 rounded-t-lg cursor-pointer"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center">
          <span className="text-sm font-mono bg-indigo-100 text-indigo-700 px-2 py-0.5 rounded mr-3">
            {node.node_id}
          </span>
          <h3 className="text-sm font-medium text-gray-900">{tool?.name || node.tool_id}</h3>
          <span className="ml-2 text-xs text-gray-500">{node.tool_id}</span>
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={(e) => { e.stopPropagation(); onRemove() }}
            className="text-red-500 hover:text-red-700 text-sm"
          >
            Remove
          </button>
          <svg className={`w-5 h-5 text-gray-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </div>

      {isExpanded && (
        <div className="px-4 py-4">
          {/* Input Mappings */}
          <div className="mb-4">
            <h4 className="text-sm font-medium text-gray-700 mb-2">Input Mappings</h4>
            {tool?.input_schema.map((param) => (
              <div key={param.name} className="mb-3 p-3 bg-gray-50 rounded">
                <div className="flex items-center justify-between mb-2">
                  <div>
                    <span className="font-mono text-sm text-indigo-600">{param.name}</span>
                    <span className="text-xs text-gray-400 ml-1">({param.type})</span>
                    {param.required && <span className="text-red-500 ml-1">*</span>}
                  </div>
                  <select
                    className="text-xs border border-gray-200 rounded px-2 py-1"
                    value={node.input_mapping[param.name]?.type || 'constant'}
                    onChange={(e) => {
                      if (e.target.value === 'constant') {
                        updateInputMapping(param.name, { type: 'constant', value: '' })
                      } else {
                        updateInputMapping(param.name, { type: 'fromNode', node_id: '', path: '' })
                      }
                    }}
                  >
                    <option value="constant">Constant</option>
                    <option value="fromNode">From Previous Node</option>
                  </select>
                </div>
                
                {/* Constant Input */}
                {(!node.input_mapping[param.name] || node.input_mapping[param.name].type === 'constant') && (
                  <>
                    {/* File Upload for file_ref parameters */}
                    {isFileRefParam(param.name) ? (
                      <div className="space-y-2">
                        <div className="flex items-center space-x-2">
                          <input
                            type="text"
                            className="flex-1 border border-gray-300 rounded px-3 py-2 text-sm bg-gray-100"
                            placeholder="file_ref will appear here"
                            value={(node.input_mapping[param.name] as any)?.value || ''}
                            readOnly
                          />
                          <label className={`px-4 py-2 text-sm font-medium rounded-md cursor-pointer ${
                            uploadingFile === param.name 
                              ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                              : 'bg-indigo-600 text-white hover:bg-indigo-700'
                          }`}>
                            {uploadingFile === param.name ? (
                              <span className="flex items-center">
                                <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                </svg>
                                Uploading...
                              </span>
                            ) : (
                              <>
                                <svg className="w-4 h-4 inline mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                                </svg>
                                Upload File
                              </>
                            )}
                            <input
                              type="file"
                              className="hidden"
                              accept=".pdf,.txt,.json,.csv"
                              disabled={uploadingFile === param.name}
                              onChange={(e) => {
                                const file = e.target.files?.[0]
                                if (file) {
                                  handleFileUpload(param.name, file)
                                }
                              }}
                            />
                          </label>
                        </div>
                        {uploadedFiles[param.name] && (
                          <div className="flex items-center text-xs text-green-600">
                            <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                            </svg>
                            Uploaded: {uploadedFiles[param.name].filename}
                          </div>
                        )}
                        <p className="text-xs text-gray-400">Supported: PDF, TXT, JSON, CSV (max 10MB)</p>
                      </div>
                    ) : (
                      <input
                        type="text"
                        className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                        placeholder={`Enter ${param.name}`}
                        value={(node.input_mapping[param.name] as any)?.value || ''}
                        onChange={(e) => {
                          let value: any = e.target.value
                          // Type conversion
                          if (param.type === 'integer') value = parseInt(value) || 0
                          if (param.type === 'number') value = parseFloat(value) || 0
                          if (param.type === 'boolean') value = value === 'true'
                          updateInputMapping(param.name, { type: 'constant', value })
                        }}
                      />
                    )}
                  </>
                )}
                
                {/* PRD 8.1: From Previous Node Dropdown */}
                {node.input_mapping[param.name]?.type === 'fromNode' && (
                  <div className="space-y-2">
                    <select
                      className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                      value={`${(node.input_mapping[param.name] as any)?.node_id}:${(node.input_mapping[param.name] as any)?.path}`}
                      onChange={(e) => {
                        const [nodeId, path] = e.target.value.split(':')
                        updateInputMapping(param.name, { type: 'fromNode', node_id: nodeId, path })
                      }}
                    >
                      <option value=":">Select output...</option>
                      {getAvailableOutputs().map((output) => (
                        <option 
                          key={`${output.nodeId}:${output.path}`} 
                          value={`${output.nodeId}:${output.path}`}
                        >
                          {output.nodeId}.{output.path} ({output.type})
                        </option>
                      ))}
                    </select>
                    <p className="text-xs text-gray-500">
                      Selected: {(node.input_mapping[param.name] as any)?.node_id || 'none'} → {(node.input_mapping[param.name] as any)?.path || 'none'}
                    </p>
                  </div>
                )}
                
                <p className="text-xs text-gray-500 mt-1">{param.description}</p>
              </div>
            ))}
          </div>

          {/* LLM Prompt Settings */}
          {tool?.has_prompt && (
            <div className="border-t pt-4">
              <h4 className="text-sm font-medium text-gray-700 mb-2">LLM Prompt</h4>
              
              <div className="mb-3">
                <label className="block text-xs text-gray-600 mb-1">System Prompt</label>
                <textarea
                  className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                  rows={2}
                  placeholder="You are a helpful assistant."
                  value={node.prompt?.system || ''}
                  onChange={(e) => updatePrompt('system', e.target.value)}
                />
              </div>
              
              <div className="mb-3">
                <label className="block text-xs text-gray-600 mb-1">
                  User Prompt 
                  <span className="text-gray-400 ml-1">(use {'{{input.fieldName}}'} for variables)</span>
                </label>
                <textarea
                  className="w-full border border-gray-300 rounded px-3 py-2 text-sm font-mono"
                  rows={4}
                  placeholder="Summarize the following text:\n\n{{input.text}}"
                  value={node.prompt?.user || ''}
                  onChange={(e) => updatePrompt('user', e.target.value)}
                />
              </div>
              
              <div className="flex items-center">
                <input
                  type="checkbox"
                  id={`force-json-${node.node_id}`}
                  className="rounded border-gray-300 text-indigo-600"
                  checked={node.prompt?.force_json || false}
                  onChange={(e) => updatePrompt('force_json', e.target.checked)}
                />
                <label htmlFor={`force-json-${node.node_id}`} className="ml-2 text-sm text-gray-700">
                  Force JSON Response
                </label>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function WorkflowBuilderPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const isEdit = !!id
  
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [nodes, setNodes] = useState<WorkflowNode[]>([])
  const [tools, setTools] = useState<Tool[]>([])
  const [toolMap, setToolMap] = useState<Record<string, Tool>>({})
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [showToolSelector, setShowToolSelector] = useState(false)

  useEffect(() => {
    loadTools()
  }, [])

  useEffect(() => {
    if (isEdit && Object.keys(toolMap).length > 0) {
      loadWorkflow()
    }
  }, [id, toolMap])

  const loadTools = async () => {
    try {
      const { tools } = await toolsApi.list()
      setTools(tools)
      const map: Record<string, Tool> = {}
      tools.forEach(tool => { map[tool.tool_id] = tool })
      setToolMap(map)
    } catch (error) {
      console.error('Failed to load tools:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadWorkflow = async () => {
    if (!id) return
    
    setLoading(true)
    try {
      const workflow = await workflowsApi.get(id)
      setName(workflow.name)
      setDescription(workflow.description)
      setNodes(workflow.nodes)
    } catch (error) {
      console.error('Failed to load workflow:', error)
    } finally {
      setLoading(false)
    }
  }

  const addNode = (tool: Tool) => {
    const nodeId = `n${nodes.length + 1}`
    const newNode: WorkflowNode = {
      node_id: nodeId,
      tool_id: tool.tool_id,
      version: tool.version,
      input_mapping: {},
      prompt: tool.has_prompt ? {
        system: 'You are a helpful assistant.',
        user: '',
        force_json: false
      } : undefined
    }
    setNodes([...nodes, newNode])
    setShowToolSelector(false)
  }

  const updateNode = (index: number, node: WorkflowNode) => {
    const newNodes = [...nodes]
    newNodes[index] = node
    setNodes(newNodes)
  }

  const removeNode = (index: number) => {
    setNodes(nodes.filter((_, i) => i !== index))
  }

  const handleSave = async () => {
    if (!name.trim()) {
      alert('Please enter a workflow name')
      return
    }
    if (nodes.length === 0) {
      alert('Please add at least one node')
      return
    }

    setSaving(true)
    try {
      if (isEdit && id) {
        await workflowsApi.update(id, { name, description, nodes })
      } else {
        await workflowsApi.create({ name, description, nodes })
      }
      navigate('/workflows')
    } catch (error: any) {
      console.error('Failed to save workflow:', error)
      alert(error.response?.data?.error?.message || 'Failed to save workflow')
    } finally {
      setSaving(false)
    }
  }

  // Get previous nodes for a given index
  const getPrevNodes = (index: number) => nodes.slice(0, index)
  const getPrevOutputs = (index: number): Record<string, Tool | null> => {
    const outputs: Record<string, Tool | null> = {}
    nodes.slice(0, index).forEach(node => {
      outputs[node.node_id] = toolMap[node.tool_id] || null
    })
    return outputs
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
      </div>
    )
  }

  return (
    <div className="px-4 sm:px-0">
      <div className="sm:flex sm:items-center sm:justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            {isEdit ? 'Edit Workflow' : 'New Workflow'}
          </h1>
        </div>
        <div className="mt-4 sm:mt-0 flex space-x-3">
          <button
            onClick={() => navigate('/workflows')}
            className="px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className={`px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white ${
              saving ? 'bg-gray-400' : 'bg-indigo-600 hover:bg-indigo-700'
            }`}
          >
            {saving ? 'Saving...' : 'Save Workflow'}
          </button>
        </div>
      </div>

      {/* Workflow Details */}
      <div className="bg-white rounded-lg border border-gray-200 p-4 mb-6">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Name *</label>
            <input
              type="text"
              className="w-full border border-gray-300 rounded-md px-3 py-2"
              placeholder="My Workflow"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
            <input
              type="text"
              className="w-full border border-gray-300 rounded-md px-3 py-2"
              placeholder="Workflow description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>
        </div>
      </div>

      {/* Nodes */}
      <div className="mb-4">
        <h2 className="text-lg font-medium text-gray-900 mb-4">
          Nodes ({nodes.length})
        </h2>
        
        {nodes.map((node, index) => (
          <div key={node.node_id}>
            <NodeEditor
              node={node}
              tool={toolMap[node.tool_id] || null}
              prevNodes={getPrevNodes(index)}
              prevOutputs={getPrevOutputs(index)}
              onUpdate={(updated) => updateNode(index, updated)}
              onRemove={() => removeNode(index)}
            />
            {index < nodes.length - 1 && (
              <div className="flex justify-center my-2">
                <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
                </svg>
              </div>
            )}
          </div>
        ))}

        {/* Add Node Button */}
        {!showToolSelector ? (
          <button
            onClick={() => setShowToolSelector(true)}
            className="w-full py-3 border-2 border-dashed border-gray-300 rounded-lg text-gray-500 hover:border-indigo-500 hover:text-indigo-600 transition-colors"
          >
            <svg className="w-5 h-5 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            <span className="block mt-1 text-sm">Add Node</span>
          </button>
        ) : (
          /* Tool Selector */
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-medium text-gray-900">Select a Tool</h3>
              <button
                onClick={() => setShowToolSelector(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {tools.map((tool) => (
                <button
                  key={tool.tool_id}
                  onClick={() => addNode(tool)}
                  className="p-3 text-left border border-gray-200 rounded hover:border-indigo-500 hover:bg-indigo-50 transition-colors"
                >
                  <p className="font-medium text-sm text-gray-900">{tool.name}</p>
                  <p className="text-xs text-gray-500 font-mono">{tool.tool_id}</p>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default WorkflowBuilderPage
