module.exports = {
  apps: [
    {
      name: "bot-financeiro",
      script: "uvicorn",
      args: "app.main:app --host 0.0.0.0 --port 8000",
      // 'none' tells PM2 not to use a specific interpreter like node, 
      // allowing it to run the 'uvicorn' executable directly.
      interpreter: "none",
      autorestart: true,
    },
  ],
};