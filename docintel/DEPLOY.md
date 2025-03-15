# Deploying to Render

This guide will help you deploy the Document Intelligence application to Render.

## Prerequisites

1. Create a Render account: https://render.com/
2. Have a GitHub repository with your code (optional, but recommended)

## Deployment Steps

### 1. Build the Frontend

The frontend must be built and copied to the backend before deployment:

```bash
# Navigate to the frontend directory
cd frontend

# Build the React application
npm run build:backend
```

This script will build the React app and automatically copy the files to the backend's build directory.

### 2. Deploy to Render

#### Option 1: Deploy via render.yaml (Recommended)

1. **Push your code to GitHub** (if you haven't already)

2. **Connect your GitHub repository to Render**:
   - In the Render dashboard, go to "Blueprint" in the sidebar
   - Click "New Blueprint Instance"
   - Connect your GitHub repository
   - Render will automatically detect the `render.yaml` file and set up your services

3. **Configure environment variables**:
   - After the services are created, go to each service
   - Navigate to the "Environment" tab
   - Add your sensitive environment variables:
     - `OPENAI_API_KEY`
     - `AZURE_OPENAI_ENDPOINT`
     - `AZURE_OPENAI_API_KEY`
     - `GROQ_API_KEY`
     - Any other required variables

#### Option 2: Manual Deployment

1. **Create a new Web Service**:
   - From the Render dashboard, click "New" and select "Web Service"
   - Connect your GitHub repository
   - Configure the service:
     - Name: `docintel`
     - Environment: `Docker`
     - Build Command: Leave empty (uses Dockerfile)
     - Start Command: Leave empty (uses CMD in Dockerfile)

2. **Set up disk storage**:
   - In your web service, go to the "Disks" tab
   - Create a new disk:
     - Name: `docintel-storage`
     - Mount Path: `/app/uploads`
     - Size: 10 GB (or as needed)

3. **Configure environment variables**:
   - In your web service, go to the "Environment" tab
   - Add the following variables:
     - `PORT`: `8000`
     - `PYTHONPATH`: `/app`
     - `OPENAI_API_KEY`: Your OpenAI API key
     - Other required API keys and environment variables

4. **Deploy the service**:
   - Render will automatically build and deploy your service
   - You can monitor the deployment status in the "Events" tab

### 3. Access Your Application

Once deployed, your application will be available at the URL provided by Render, typically in the format:
`https://docintel.onrender.com`

## Troubleshooting

### View Logs

View the application logs for debugging:
- In the Render dashboard, select your service
- Go to the "Logs" tab to view real-time logs

### Update Environment Variables

If you need to update environment variables:
- In the Render dashboard, select your service
- Go to the "Environment" tab
- Add or update variables as needed
- The service will automatically restart with the new variables

## Updating the Application

To update your application, follow these steps:

1. Make changes to your code
2. Rebuild the frontend if needed:
   ```bash
   cd frontend
   npm run build:backend
   ```
3. Commit and push your changes to GitHub
4. Render will automatically detect the changes and redeploy your application

Alternatively, you can manually trigger a deploy from the Render dashboard by clicking "Manual Deploy" > "Deploy latest commit". 