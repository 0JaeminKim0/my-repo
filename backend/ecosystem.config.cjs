module.exports = {
  apps: [
    {
      name: 'workflow-platform',
      script: 'python',
      args: '-m uvicorn app.main:app --host 0.0.0.0 --port 3000',
      cwd: '/home/user/webapp/backend',
      env: {
        PYTHONUNBUFFERED: '1'
      },
      watch: false,
      instances: 1,
      exec_mode: 'fork'
    }
  ]
}
