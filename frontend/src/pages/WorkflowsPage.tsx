import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { workflowsApi, runsApi } from '../services/api'
import type { Workflow } from '../types'

function WorkflowsPage() {
  const [workflows, setWorkflows] = useState<Workflow[]>([])
  const [loading, setLoading] = useState(true)
  const [runningWorkflow, setRunningWorkflow] = useState<string | null>(null)
  const navigate = useNavigate()

  useEffect(() => {
    loadWorkflows()
  }, [])

  const loadWorkflows = async () => {
    setLoading(true)
    try {
      const { workflows } = await workflowsApi.list()
      setWorkflows(workflows)
    } catch (error) {
      console.error('Failed to load workflows:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (workflowId: string) => {
    if (!confirm('Are you sure you want to delete this workflow?')) return
    
    try {
      await workflowsApi.delete(workflowId)
      setWorkflows(workflows.filter((w) => w.workflow_id !== workflowId))
    } catch (error) {
      console.error('Failed to delete workflow:', error)
      alert('Failed to delete workflow')
    }
  }

  const handleRun = async (workflowId: string) => {
    setRunningWorkflow(workflowId)
    try {
      const run = await runsApi.create(workflowId)
      navigate(`/runs/${run.run_id}`)
    } catch (error: any) {
      console.error('Failed to run workflow:', error)
      alert(error.response?.data?.error?.message || 'Failed to run workflow')
    } finally {
      setRunningWorkflow(null)
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString()
  }

  return (
    <div className="px-4 sm:px-0">
      <div className="sm:flex sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Workflows</h1>
          <p className="mt-1 text-sm text-gray-500">
            여러 Tool을 연결하여 업무를 자동화하는 Workflow를 관리합니다.
          </p>
        </div>
        <div className="mt-4 sm:mt-0">
          <Link
            to="/workflows/new"
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700"
          >
            <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            New Workflow
          </Link>
        </div>
      </div>

      {loading ? (
        <div className="mt-6 text-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mx-auto"></div>
          <p className="mt-2 text-sm text-gray-500">Loading workflows...</p>
        </div>
      ) : (
        <div className="mt-6">
          {workflows.length > 0 ? (
            <div className="bg-white shadow overflow-hidden sm:rounded-md">
              <ul className="divide-y divide-gray-200">
                {workflows.map((workflow) => (
                  <li key={workflow.workflow_id}>
                    <div className="px-4 py-4 sm:px-6 hover:bg-gray-50">
                      <div className="flex items-center justify-between">
                        <div className="flex-1 min-w-0">
                          <Link
                            to={`/workflows/${workflow.workflow_id}`}
                            className="text-lg font-medium text-indigo-600 hover:text-indigo-800 truncate"
                          >
                            {workflow.name}
                          </Link>
                          <p className="mt-1 text-sm text-gray-500 truncate">
                            {workflow.description || 'No description'}
                          </p>
                          <div className="mt-2 flex items-center text-sm text-gray-500">
                            <span className="font-mono text-xs bg-gray-100 px-2 py-0.5 rounded">
                              {workflow.workflow_id}
                            </span>
                            <span className="mx-2">•</span>
                            <span>{workflow.nodes.length} nodes</span>
                            <span className="mx-2">•</span>
                            <span>Updated {formatDate(workflow.updated_at)}</span>
                          </div>
                        </div>
                        <div className="flex items-center space-x-2 ml-4">
                          <button
                            onClick={() => handleRun(workflow.workflow_id)}
                            disabled={runningWorkflow === workflow.workflow_id}
                            className={`inline-flex items-center px-3 py-1.5 border border-transparent text-sm font-medium rounded-md shadow-sm text-white ${
                              runningWorkflow === workflow.workflow_id
                                ? 'bg-gray-400 cursor-not-allowed'
                                : 'bg-green-600 hover:bg-green-700'
                            }`}
                          >
                            {runningWorkflow === workflow.workflow_id ? (
                              <>
                                <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-white mr-2"></div>
                                Running...
                              </>
                            ) : (
                              <>
                                <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                </svg>
                                Run
                              </>
                            )}
                          </button>
                          <Link
                            to={`/workflows/${workflow.workflow_id}`}
                            className="inline-flex items-center px-3 py-1.5 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                          >
                            Edit
                          </Link>
                          <button
                            onClick={() => handleDelete(workflow.workflow_id)}
                            className="inline-flex items-center px-3 py-1.5 border border-red-300 text-sm font-medium rounded-md text-red-700 bg-white hover:bg-red-50"
                          >
                            Delete
                          </button>
                        </div>
                      </div>
                      
                      {/* Node Summary */}
                      {workflow.nodes.length > 0 && (
                        <div className="mt-3 flex flex-wrap gap-2">
                          {workflow.nodes.map((node, idx) => (
                            <div key={node.node_id} className="flex items-center">
                              <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-800">
                                {node.tool_id}
                              </span>
                              {idx < workflow.nodes.length - 1 && (
                                <svg className="w-4 h-4 text-gray-400 mx-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                                </svg>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            <div className="text-center py-12 bg-white rounded-lg border border-gray-200">
              <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
              <h3 className="mt-2 text-sm font-medium text-gray-900">No workflows</h3>
              <p className="mt-1 text-sm text-gray-500">Get started by creating a new workflow.</p>
              <div className="mt-6">
                <Link
                  to="/workflows/new"
                  className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700"
                >
                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                  New Workflow
                </Link>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default WorkflowsPage
