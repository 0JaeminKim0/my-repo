import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { runsApi, workflowsApi } from '../services/api'
import type { Run, Workflow, NodeTrace } from '../types'

// Markdown 텍스트인지 판단
function isMarkdownText(value: unknown): boolean {
  if (typeof value !== 'string') return false
  // Markdown 특징: 헤더, 리스트, 코드블록, 링크, 테이블 등
  const markdownPatterns = [
    /^#{1,6}\s/m,           // 헤더
    /^\s*[-*+]\s/m,         // 리스트
    /^\s*\d+\.\s/m,         // 숫자 리스트
    /```[\s\S]*```/,        // 코드블록
    /\[.*\]\(.*\)/,         // 링크
    /\|.*\|.*\|/,           // 테이블
    /\*\*.*\*\*/,           // 볼드
    /^\s*>/m,               // 인용
  ]
  return markdownPatterns.some(pattern => pattern.test(value))
}

// Markdown 렌더러 컴포넌트
function MarkdownRenderer({ content }: { content: string }) {
  return (
    <div className="prose prose-sm max-w-none prose-headings:text-gray-800 prose-p:text-gray-600 prose-li:text-gray-600 prose-strong:text-gray-800 prose-code:bg-gray-100 prose-code:px-1 prose-code:rounded prose-pre:bg-gray-800 prose-pre:text-gray-100 prose-table:border prose-th:bg-gray-100 prose-th:p-2 prose-td:p-2 prose-td:border">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>
        {content}
      </ReactMarkdown>
    </div>
  )
}

// Output 렌더러 - Markdown이면 렌더링, 아니면 JSON
function OutputRenderer({ data, showToggle = false }: { data: unknown; showToggle?: boolean }) {
  const [viewMode, setViewMode] = useState<'rendered' | 'raw'>('rendered')
  
  // raw_text 또는 result 필드에서 Markdown 추출
  const getMarkdownContent = (obj: unknown): string | null => {
    if (typeof obj === 'string' && isMarkdownText(obj)) {
      return obj
    }
    if (typeof obj === 'object' && obj !== null) {
      const o = obj as Record<string, unknown>
      // raw_text 우선 체크
      if (typeof o.raw_text === 'string' && o.raw_text.length > 100) {
        return o.raw_text
      }
      // result가 문자열이면 체크
      if (typeof o.result === 'string' && isMarkdownText(o.result)) {
        return o.result
      }
    }
    return null
  }
  
  const markdownContent = getMarkdownContent(data)
  const hasMarkdown = markdownContent !== null
  
  if (!hasMarkdown) {
    return (
      <pre className="text-sm text-gray-700 bg-gray-50 p-4 rounded overflow-x-auto">
        {JSON.stringify(data, null, 2)}
      </pre>
    )
  }
  
  return (
    <div>
      {showToggle && (
        <div className="flex space-x-2 mb-3">
          <button
            onClick={() => setViewMode('rendered')}
            className={`px-3 py-1 text-sm rounded ${
              viewMode === 'rendered' 
                ? 'bg-indigo-600 text-white' 
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            Rendered
          </button>
          <button
            onClick={() => setViewMode('raw')}
            className={`px-3 py-1 text-sm rounded ${
              viewMode === 'raw' 
                ? 'bg-indigo-600 text-white' 
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            Raw JSON
          </button>
        </div>
      )}
      
      {viewMode === 'rendered' ? (
        <div className="bg-white border border-gray-200 rounded-lg p-4 overflow-x-auto">
          <MarkdownRenderer content={markdownContent} />
        </div>
      ) : (
        <pre className="text-sm text-gray-700 bg-gray-50 p-4 rounded overflow-x-auto">
          {JSON.stringify(data, null, 2)}
        </pre>
      )}
    </div>
  )
}

// PRD 8.2: Run Trace View
function NodeTraceCard({ trace, isLast }: { trace: NodeTrace; isLast: boolean }) {
  const [isExpanded, setIsExpanded] = useState(trace.status === 'FAILED')

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'SUCCESS':
        return 'bg-green-500'
      case 'FAILED':
        return 'bg-red-500'
      case 'RUNNING':
        return 'bg-blue-500 animate-pulse'
      case 'PENDING':
        return 'bg-gray-300'
      case 'SKIPPED':
        return 'bg-gray-400'
      default:
        return 'bg-gray-300'
    }
  }

  const getStatusBg = (status: string) => {
    switch (status) {
      case 'SUCCESS':
        return 'bg-green-50 border-green-200'
      case 'FAILED':
        return 'bg-red-50 border-red-200'
      case 'RUNNING':
        return 'bg-blue-50 border-blue-200'
      default:
        return 'bg-gray-50 border-gray-200'
    }
  }

  const formatDuration = (start?: string, end?: string) => {
    if (!start || !end) return '-'
    const ms = new Date(end).getTime() - new Date(start).getTime()
    if (ms < 1000) return `${ms}ms`
    return `${(ms / 1000).toFixed(2)}s`
  }

  return (
    <div className="relative">
      {/* Timeline connector */}
      {!isLast && (
        <div className="absolute left-4 top-10 bottom-0 w-0.5 bg-gray-200" />
      )}
      
      <div className={`relative flex items-start mb-4 ${trace.status === 'FAILED' ? 'z-10' : ''}`}>
        {/* Status indicator */}
        <div className={`flex-shrink-0 w-8 h-8 rounded-full ${getStatusColor(trace.status)} flex items-center justify-center`}>
          {trace.status === 'SUCCESS' && (
            <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
            </svg>
          )}
          {trace.status === 'FAILED' && (
            <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M6 18L18 6M6 6l12 12" />
            </svg>
          )}
          {trace.status === 'RUNNING' && (
            <svg className="w-4 h-4 text-white animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
          )}
        </div>
        
        {/* Card */}
        <div className={`ml-4 flex-1 rounded-lg border p-4 ${getStatusBg(trace.status)}`}>
          {/* Header */}
          <div 
            className="flex items-center justify-between cursor-pointer"
            onClick={() => setIsExpanded(!isExpanded)}
          >
            <div className="flex items-center space-x-3">
              <span className="font-mono text-sm font-medium text-indigo-600 bg-indigo-100 px-2 py-0.5 rounded">
                {trace.node_id}
              </span>
              <span className="font-medium text-gray-900">{trace.tool_id}</span>
              <span className="text-sm text-gray-500">
                {formatDuration(trace.started_at, trace.ended_at)}
              </span>
            </div>
            <div className="flex items-center space-x-2">
              <span className={`px-2 py-0.5 text-xs font-medium rounded ${
                trace.status === 'SUCCESS' ? 'bg-green-100 text-green-800' :
                trace.status === 'FAILED' ? 'bg-red-100 text-red-800' :
                'bg-gray-100 text-gray-800'
              }`}>
                {trace.status}
              </span>
              <svg className={`w-5 h-5 text-gray-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </div>
          </div>
          
          {/* Expanded Details */}
          {isExpanded && (
            <div className="mt-4 pt-4 border-t border-gray-200">
              {/* Error Message - PRD 8.2: 실패 Node 강조 */}
              {trace.error && (
                <div className="mb-4 p-3 bg-red-100 border border-red-200 rounded-lg">
                  <h4 className="text-sm font-medium text-red-800 mb-1">Error: {trace.error.code}</h4>
                  <p className="text-sm text-red-700">{trace.error.message}</p>
                  {Object.keys(trace.error.details).length > 0 && (
                    <pre className="mt-2 text-xs text-red-600 bg-red-50 p-2 rounded overflow-x-auto">
                      {JSON.stringify(trace.error.details, null, 2)}
                    </pre>
                  )}
                </div>
              )}
              
              {/* Input Summary - PRD 8.2: 입력 요약 */}
              <div className="mb-3">
                <h4 className="text-sm font-medium text-gray-700 mb-1">Input</h4>
                <pre className="text-xs text-gray-600 bg-gray-100 p-2 rounded overflow-x-auto max-h-40">
                  {JSON.stringify(trace.input_summary, null, 2)}
                </pre>
              </div>
              
              {/* Output Summary - PRD 8.2: 출력 요약 (Markdown 지원) */}
              {trace.status === 'SUCCESS' && (
                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-1">Output</h4>
                  <div className="bg-gray-100 p-2 rounded overflow-x-auto max-h-96">
                    <OutputRenderer data={trace.output_summary} />
                  </div>
                </div>
              )}
              
              {/* Timestamps */}
              <div className="mt-3 text-xs text-gray-500 flex space-x-4">
                {trace.started_at && (
                  <span>Started: {new Date(trace.started_at).toLocaleTimeString()}</span>
                )}
                {trace.ended_at && (
                  <span>Ended: {new Date(trace.ended_at).toLocaleTimeString()}</span>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function RunDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [run, setRun] = useState<Run | null>(null)
  const [workflow, setWorkflow] = useState<Workflow | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadRun()
  }, [id])

  const loadRun = async () => {
    if (!id) return
    
    setLoading(true)
    try {
      const runData = await runsApi.get(id)
      setRun(runData)
      
      // Load workflow info
      try {
        const wfData = await workflowsApi.get(runData.workflow_id)
        setWorkflow(wfData)
      } catch (error) {
        console.error('Failed to load workflow:', error)
      }
    } catch (error) {
      console.error('Failed to load run:', error)
    } finally {
      setLoading(false)
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'SUCCESS':
        return 'bg-green-100 text-green-800 border-green-200'
      case 'FAILED':
        return 'bg-red-100 text-red-800 border-red-200'
      case 'RUNNING':
        return 'bg-blue-100 text-blue-800 border-blue-200'
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200'
    }
  }

  const formatDuration = (start?: string, end?: string) => {
    if (!start || !end) return '-'
    const ms = new Date(end).getTime() - new Date(start).getTime()
    if (ms < 1000) return `${ms}ms`
    if (ms < 60000) return `${(ms / 1000).toFixed(2)}s`
    return `${(ms / 60000).toFixed(2)}m`
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
      </div>
    )
  }

  if (!run) {
    return (
      <div className="text-center py-12">
        <h2 className="text-xl font-medium text-gray-900">Run not found</h2>
        <Link to="/runs" className="mt-4 text-indigo-600 hover:text-indigo-800">
          Back to Runs
        </Link>
      </div>
    )
  }

  return (
    <div className="px-4 sm:px-0">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center space-x-2 text-sm text-gray-500 mb-2">
          <Link to="/runs" className="hover:text-indigo-600">Runs</Link>
          <span>/</span>
          <span className="font-mono">{run.run_id}</span>
        </div>
        
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              Run Details
            </h1>
            {workflow && (
              <p className="mt-1 text-sm text-gray-500">
                Workflow: <Link to={`/workflows/${workflow.workflow_id}`} className="text-indigo-600 hover:text-indigo-800">{workflow.name}</Link>
              </p>
            )}
          </div>
          
          {/* PRD 8.2: 전체 상태 */}
          <span className={`px-4 py-2 text-lg font-medium rounded-lg border ${getStatusColor(run.status)}`}>
            {run.status}
          </span>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 mb-6">
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <p className="text-xs text-gray-500 uppercase tracking-wider">Duration</p>
          <p className="mt-1 text-2xl font-semibold text-gray-900">
            {formatDuration(run.meta.started_at, run.meta.ended_at)}
          </p>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <p className="text-xs text-gray-500 uppercase tracking-wider">Total Tokens</p>
          <p className="mt-1 text-2xl font-semibold text-gray-900">
            {run.meta.cost.tokens.toLocaleString()}
          </p>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <p className="text-xs text-gray-500 uppercase tracking-wider">Nodes</p>
          <p className="mt-1 text-2xl font-semibold text-gray-900">
            {run.trace.length}
          </p>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <p className="text-xs text-gray-500 uppercase tracking-wider">Created</p>
          <p className="mt-1 text-sm font-medium text-gray-900">
            {new Date(run.created_at).toLocaleString()}
          </p>
        </div>
      </div>

      {/* Global Error */}
      {run.error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
          <h3 className="text-lg font-medium text-red-800 mb-2">Execution Failed</h3>
          <p className="text-red-700">{run.error.message}</p>
          <p className="text-sm text-red-600 mt-1">Error code: {run.error.code}</p>
        </div>
      )}

      {/* PRD 8.2: Node별 실행 결과 타임라인 */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">Execution Timeline</h2>
        
        {run.trace.length > 0 ? (
          <div className="pl-2">
            {run.trace.map((trace, index) => (
              <NodeTraceCard 
                key={trace.node_id} 
                trace={trace} 
                isLast={index === run.trace.length - 1}
              />
            ))}
          </div>
        ) : (
          <p className="text-gray-500 text-center py-8">No execution trace available</p>
        )}
      </div>

      {/* Final Output - Markdown 렌더링 + 토글 */}
      {run.final_output && (
        <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">Final Output</h2>
          <OutputRenderer data={run.final_output} showToggle={true} />
        </div>
      )}

      {/* All Node Outputs */}
      {Object.keys(run.node_outputs).length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">All Node Outputs</h2>
          <div className="space-y-4">
            {Object.entries(run.node_outputs).map(([nodeId, output]) => (
              <div key={nodeId} className="border border-gray-200 rounded-lg p-4">
                <h3 className="font-mono text-sm font-medium text-indigo-600 mb-2">{nodeId}</h3>
                <OutputRenderer data={output} showToggle={true} />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default RunDetailPage
