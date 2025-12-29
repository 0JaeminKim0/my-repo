import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { runsApi, workflowsApi } from '../services/api'
import type { Run, Workflow } from '../types'

function RunsPage() {
  const [runs, setRuns] = useState<Run[]>([])
  const [workflows, setWorkflows] = useState<Record<string, Workflow>>({})
  const [filterWorkflowId, setFilterWorkflowId] = useState<string>('')
  const [filterStatus, setFilterStatus] = useState<string>('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadWorkflows()
    loadRuns()
  }, [])

  useEffect(() => {
    loadRuns()
  }, [filterWorkflowId, filterStatus])

  const loadWorkflows = async () => {
    try {
      const { workflows: wfList } = await workflowsApi.list()
      const wfMap: Record<string, Workflow> = {}
      wfList.forEach(wf => { wfMap[wf.workflow_id] = wf })
      setWorkflows(wfMap)
    } catch (error) {
      console.error('Failed to load workflows:', error)
    }
  }

  const loadRuns = async () => {
    setLoading(true)
    try {
      const { runs } = await runsApi.list(
        filterWorkflowId || undefined,
        filterStatus || undefined
      )
      setRuns(runs)
    } catch (error) {
      console.error('Failed to load runs:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (runId: string) => {
    if (!confirm('Are you sure you want to delete this run?')) return
    
    try {
      await runsApi.delete(runId)
      setRuns(runs.filter((r) => r.run_id !== runId))
    } catch (error) {
      console.error('Failed to delete run:', error)
      alert('Failed to delete run')
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'SUCCESS':
        return 'bg-green-100 text-green-800'
      case 'FAILED':
        return 'bg-red-100 text-red-800'
      case 'RUNNING':
        return 'bg-blue-100 text-blue-800'
      case 'PENDING':
        return 'bg-gray-100 text-gray-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString()
  }

  const formatDuration = (start?: string, end?: string) => {
    if (!start || !end) return '-'
    const ms = new Date(end).getTime() - new Date(start).getTime()
    if (ms < 1000) return `${ms}ms`
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
    return `${(ms / 60000).toFixed(1)}m`
  }

  return (
    <div className="px-4 sm:px-0">
      <div className="sm:flex sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Runs</h1>
          <p className="mt-1 text-sm text-gray-500">
            Workflow 실행 기록입니다. 각 Run의 상세 Trace를 확인할 수 있습니다.
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="mt-4 flex flex-wrap gap-4">
        <div>
          <label className="block text-xs text-gray-500 mb-1">Workflow</label>
          <select
            className="border border-gray-300 rounded-md px-3 py-1.5 text-sm"
            value={filterWorkflowId}
            onChange={(e) => setFilterWorkflowId(e.target.value)}
          >
            <option value="">All Workflows</option>
            {Object.values(workflows).map((wf) => (
              <option key={wf.workflow_id} value={wf.workflow_id}>
                {wf.name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Status</label>
          <select
            className="border border-gray-300 rounded-md px-3 py-1.5 text-sm"
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
          >
            <option value="">All Statuses</option>
            <option value="SUCCESS">SUCCESS</option>
            <option value="FAILED">FAILED</option>
            <option value="RUNNING">RUNNING</option>
            <option value="PENDING">PENDING</option>
          </select>
        </div>
      </div>

      {loading ? (
        <div className="mt-6 text-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mx-auto"></div>
          <p className="mt-2 text-sm text-gray-500">Loading runs...</p>
        </div>
      ) : (
        <div className="mt-6">
          {runs.length > 0 ? (
            <div className="bg-white shadow overflow-hidden sm:rounded-lg">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Run ID
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Workflow
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Duration
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Tokens
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Created
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {runs.map((run) => (
                    <tr key={run.run_id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <Link
                          to={`/runs/${run.run_id}`}
                          className="text-sm font-mono text-indigo-600 hover:text-indigo-800"
                        >
                          {run.run_id}
                        </Link>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-900">
                          {workflows[run.workflow_id]?.name || 'Unknown'}
                        </div>
                        <div className="text-xs text-gray-500 font-mono">
                          {run.workflow_id}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(run.status)}`}>
                          {run.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {formatDuration(run.meta.started_at, run.meta.ended_at)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {run.meta.cost.tokens > 0 ? run.meta.cost.tokens.toLocaleString() : '-'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {formatDate(run.created_at)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        <Link
                          to={`/runs/${run.run_id}`}
                          className="text-indigo-600 hover:text-indigo-900 mr-4"
                        >
                          View
                        </Link>
                        <button
                          onClick={() => handleDelete(run.run_id)}
                          className="text-red-600 hover:text-red-900"
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-center py-12 bg-white rounded-lg border border-gray-200">
              <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
              <h3 className="mt-2 text-sm font-medium text-gray-900">No runs found</h3>
              <p className="mt-1 text-sm text-gray-500">
                Run a workflow to see execution history here.
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default RunsPage
