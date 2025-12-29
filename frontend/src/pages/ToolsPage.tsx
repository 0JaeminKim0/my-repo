import { useState, useEffect } from 'react'
import { toolsApi } from '../services/api'
import type { Tool } from '../types'

function ToolsPage() {
  const [tools, setTools] = useState<Tool[]>([])
  const [categories, setCategories] = useState<string[]>([])
  const [selectedCategory, setSelectedCategory] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [expandedTool, setExpandedTool] = useState<string | null>(null)

  useEffect(() => {
    loadCategories()
    loadTools()
  }, [])

  useEffect(() => {
    loadTools(selectedCategory)
  }, [selectedCategory])

  const loadCategories = async () => {
    try {
      const { categories } = await toolsApi.getCategories()
      setCategories(categories)
    } catch (error) {
      console.error('Failed to load categories:', error)
    }
  }

  const loadTools = async (category?: string) => {
    setLoading(true)
    try {
      const { tools } = await toolsApi.list(category || undefined)
      setTools(tools)
    } catch (error) {
      console.error('Failed to load tools:', error)
    } finally {
      setLoading(false)
    }
  }

  const getCategoryColor = (category: string) => {
    const colors: Record<string, string> = {
      file: 'bg-blue-100 text-blue-800',
      llm: 'bg-purple-100 text-purple-800',
      text: 'bg-green-100 text-green-800',
      data: 'bg-orange-100 text-orange-800',
      general: 'bg-gray-100 text-gray-800'
    }
    return colors[category] || colors.general
  }

  return (
    <div className="px-4 sm:px-0">
      <div className="sm:flex sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Tools</h1>
          <p className="mt-1 text-sm text-gray-500">
            사용 가능한 Tool 목록입니다. Workflow에서 이 Tool들을 연결하여 업무를 자동화할 수 있습니다.
          </p>
        </div>
      </div>

      {/* Category Filter */}
      <div className="mt-4 flex flex-wrap gap-2">
        <button
          onClick={() => setSelectedCategory('')}
          className={`px-3 py-1.5 text-sm font-medium rounded-full ${
            selectedCategory === ''
              ? 'bg-indigo-600 text-white'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          All
        </button>
        {categories.map((category) => (
          <button
            key={category}
            onClick={() => setSelectedCategory(category)}
            className={`px-3 py-1.5 text-sm font-medium rounded-full ${
              selectedCategory === category
                ? 'bg-indigo-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            {category}
          </button>
        ))}
      </div>

      {/* Tools Grid */}
      {loading ? (
        <div className="mt-6 text-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mx-auto"></div>
          <p className="mt-2 text-sm text-gray-500">Loading tools...</p>
        </div>
      ) : (
        <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {tools.map((tool) => (
            <div
              key={tool.tool_id}
              className="bg-white rounded-lg border border-gray-200 shadow-sm hover:shadow-md transition-shadow"
            >
              <div className="p-4">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <h3 className="text-lg font-medium text-gray-900">
                      {tool.name}
                    </h3>
                    <p className="text-sm text-gray-500 font-mono">
                      {tool.tool_id}
                    </p>
                  </div>
                  <span className={`px-2 py-1 text-xs font-medium rounded ${getCategoryColor(tool.category)}`}>
                    {tool.category}
                  </span>
                </div>
                <p className="mt-2 text-sm text-gray-600">
                  {tool.description}
                </p>
                
                {/* Toggle Details */}
                <button
                  onClick={() => setExpandedTool(expandedTool === tool.tool_id ? null : tool.tool_id)}
                  className="mt-3 text-sm text-indigo-600 hover:text-indigo-800"
                >
                  {expandedTool === tool.tool_id ? 'Hide details' : 'Show details'}
                </button>
                
                {/* Expanded Details */}
                {expandedTool === tool.tool_id && (
                  <div className="mt-3 pt-3 border-t border-gray-100">
                    {/* Input Schema */}
                    <div className="mb-3">
                      <h4 className="text-sm font-medium text-gray-700">Input</h4>
                      <ul className="mt-1 space-y-1">
                        {tool.input_schema.map((param) => (
                          <li key={param.name} className="text-sm">
                            <span className="font-mono text-indigo-600">{param.name}</span>
                            <span className="text-gray-400 ml-1">({param.type})</span>
                            {param.required && <span className="text-red-500 ml-1">*</span>}
                            <p className="text-gray-500 text-xs ml-2">{param.description}</p>
                          </li>
                        ))}
                      </ul>
                    </div>
                    
                    {/* Output Schema */}
                    <div>
                      <h4 className="text-sm font-medium text-gray-700">Output</h4>
                      <ul className="mt-1 space-y-1">
                        {tool.output_schema.map((param) => (
                          <li key={param.name} className="text-sm">
                            <span className="font-mono text-green-600">{param.name}</span>
                            <span className="text-gray-400 ml-1">({param.type})</span>
                            <p className="text-gray-500 text-xs ml-2">{param.description}</p>
                          </li>
                        ))}
                      </ul>
                    </div>
                    
                    {tool.has_prompt && (
                      <div className="mt-2">
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-800">
                          LLM Prompt Tool
                        </span>
                      </div>
                    )}
                  </div>
                )}
              </div>
              
              <div className="px-4 py-2 bg-gray-50 border-t border-gray-100 rounded-b-lg">
                <span className="text-xs text-gray-500">v{tool.version}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {!loading && tools.length === 0 && (
        <div className="mt-6 text-center py-12 bg-white rounded-lg border border-gray-200">
          <p className="text-gray-500">No tools found</p>
        </div>
      )}
    </div>
  )
}

export default ToolsPage
