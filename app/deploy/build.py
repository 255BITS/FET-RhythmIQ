import os
import argparse
import subprocess
import json

def get_ecr_uri(service):
    """Retrieve the ECR URI dynamically from AWS based on the service repository name."""
    account_id = subprocess.check_output(
        ['aws', 'sts', 'get-caller-identity', '--query', 'Account', '--output', 'text']
    ).decode().strip()
    
    region = os.getenv('AWS_DEFAULT_REGION', 'us-west-2')
    ecr_uri = f"{account_id}.dkr.ecr.{region}.amazonaws.com"
    
    # Check if the repository exists
    repositories = subprocess.check_output(
        ['aws', 'ecr', 'describe-repositories', '--query', 'repositories[*].repositoryName', '--output', 'json']
    ).decode()
    
    if service not in json.loads(repositories):
        raise ValueError(f"ECR repository '{service}' not found.")
    
    return f"{ecr_uri}/{service}"

def docker_build_push(service_path, service, ecr, version):
    # original_dir is the current directory (project-root/app/deploy)
    original_dir = os.getcwd()
    # Determine the project root (two levels up from app/deploy)
    project_root = os.path.abspath(os.path.join(original_dir, "..", ".."))
    
    # Compute full path to the Dockerfile
    dockerfile_path = os.path.join(project_root, service_path)
    
    # Build context is the project root
    cmd = [
        'docker',
        'buildx',
        'build',
        '--platform',
        'linux/arm64',
        '-t',
        f'{ecr}:{version}',
        '-f',
        dockerfile_path,
        '--push',
        project_root
    ]
    print("-- Running Docker Build and Push for Service:", service)
    subprocess.check_call(cmd, cwd=project_root)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('pattern', nargs='?', default=None)
    args = parser.parse_args()

    print("Logging into AWS ECR")
    aws_password = subprocess.check_output(['aws', 'ecr', 'get-login-password']).decode().strip()

    version = os.getenv('VERSION', '1.0')
    # Use paths relative to the project root
    service_paths = {
        'rhythmiq': 'app/Dockerfile',
        'rhythmiqagent': 'agent/Dockerfile'
    }
    services = service_paths.keys()

    for service in services:
        if args.pattern is None or args.pattern in service:
            service_path = service_paths.get(service)
            ecr = get_ecr_uri(service)  # Dynamically retrieve ECR URI
            subprocess.run(
                ['docker', 'login', '--username', 'AWS', '--password-stdin', ecr],
                input=aws_password, text=True, check=True
            )
            docker_build_push(service_path, service, ecr, version)
        else:
            print("Skipping", service)

    print("Project has been built but not redeployed.  To redeploy run:")
    print("   python deploy.py")

if __name__ == '__main__':
    main()
