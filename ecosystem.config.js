module.exports = {
  apps: [
    {
      name: "whatsapp-engine",
      script: "server.js",
      env: {
        NODE_ENV: "production",
        PORT: 8080
      }
    },
    {
      name: "telegram-bot",
      script: "bot.py",
      interpreter: "python3",
      env: {
        PYTHONUNBUFFERED: "1"
      }
    }
  ]
};