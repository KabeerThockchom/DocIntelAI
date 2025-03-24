# Deploying DocIntel to Fly.io

This guide will walk you through deploying your DocIntel application to Fly.io.

## Prerequisites

1. Install the Fly CLI:
   ```bash
   brew install flyctl
   ```

2. Sign up and log in to Fly:
   ```bash
   fly auth signup
   # or if you already have an account
   fly auth login
   ```

## Deployment Steps

1. Navigate to your project directory:
   ```bash
   cd docintel
   ```

2. Launch your app on Fly:
   ```bash
   fly launch
   ```
   - This will detect your fly.toml and Dockerfile
   - When prompted, select "No" for creating a PostgreSQL database unless you need one
   - When prompted, select "No" for creating a Redis database unless you need one
   - When prompted to deploy now, you can say "No" as we need to set up environment variables first

3. Create a volume for persistent storage:
   ```bash
   fly volumes create docintel_data --size 10 --region sea
   ```
   Note: Replace "sea" with your preferred region if different

4. Set up environment variables:
   ```bash
   fly secrets set $(cat .env | xargs)
   ```
   This will set all the variables from your .env file as secrets on Fly.io

5. Deploy the application:
   ```bash
   fly deploy
   ```

6. Open your deployed application:
   ```bash
   fly open
   ```

## Monitoring and Maintenance

- View logs:
  ```bash
  fly logs
  ```

- SSH into your running application:
  ```bash
  fly ssh console
  ```

- Scale your application:
  ```bash
  fly scale count 2  # Increase to 2 instances
  ```

- Restart your application:
  ```bash
  fly apps restart
  ```

## Troubleshooting

- If your application fails to start, check the logs:
  ```bash
  fly logs
  ```

- Check the status of your application:
  ```bash
  fly status
  ```

- If you need to make changes to your configuration, edit the fly.toml file and redeploy:
  ```bash
  fly deploy
  ```

## Important Notes

1. Your application is configured to mount a volume at `/app/app/storage` for persistent data storage
2. Environment variables are set using Fly secrets and not stored in the fly.toml file
3. The application is set to run on port 8000 internally, but Fly.io handles routing from ports 80/443 