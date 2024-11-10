import subprocess
import argparse
import sys
import os
import json

def get_manager_ip():
    """Find the IP of the EC2 instance named 'docker-manager'."""
    try:
        response = subprocess.check_output(
            [
                'aws', 'ec2', 'describe-instances',
                '--filters', 'Name=tag:Name,Values=docker-manager',
                '--query', 'Reservations[*].Instances[*].PublicIpAddress',
                '--output', 'text'
            ]
        ).decode().strip()
        
        if not response:
            raise ValueError("No instance found with the name 'docker-manager'. Ensure the EC2 instance is running and correctly tagged.")
        
        return response
    except subprocess.CalledProcessError as e:
        print(f"Failed to retrieve manager IP: {e}", file=sys.stderr)
        sys.exit(1)

def get_ecr_uri():
    """Dynamically retrieve the ECR URI using AWS CLI."""
    account_id = subprocess.check_output(
        ['aws', 'sts', 'get-caller-identity', '--query', 'Account', '--output', 'text']
    ).decode().strip()
    region = os.getenv('AWS_DEFAULT_REGION', 'us-west-2')
    return f"{account_id}.dkr.ecr.{region}.amazonaws.com"

def ecr_login(manager, key, ecr_uri):
    """Logs into AWS ECR on the remote manager node."""
    get_login_password_cmd = "aws ecr get-login-password --region us-west-2"
    docker_login_cmd = f"{get_login_password_cmd} | sudo docker login --username AWS --password-stdin {ecr_uri}"
    ssh_command = f"ssh -i {key} {manager} '{docker_login_cmd}'"
    subprocess.check_call(ssh_command, shell=True)

def parse_arguments():
    parser = argparse.ArgumentParser(description='Deploy services to Docker Swarm.')
    parser.add_argument('project', help='Specify the project to deploy.')
    parser.add_argument('--manager', default='auto', help='Specify the Docker Swarm manager host or use "auto" to find it by name.')
    parser.add_argument('--key', required=True, help='Specify the SSH key path.')
    return parser.parse_args()

def file_exists(project):
    return os.path.isfile(f'./docker-swarm/{project}.yml')

def sync_files(project, manager, key):
    subprocess.check_call(['rsync', '-avz', '-e', f'ssh -i {key}', f'./secrets/{project}.yml', f'{manager}:~/'])

def deploy_stack(project, manager, key):
    deploy_command = f'sudo docker stack deploy --compose-file ~/{project}.yml --with-registry-auth {project} --resolve-image always'
    ssh_command = f'ssh -i {key} {manager} \"{deploy_command}\"'
    subprocess.check_call(ssh_command, shell=True)

def read_env_file(filename):
    """Reads secrets from a file and returns them as a dictionary."""
    env_variables = {}
    with open(filename, 'r') as file:
        for line in file:
            line = line.strip()
            if line:
                key, value = line.split('=', 1)
                env_variables[key] = value
    return env_variables

def replace_secrets(ymlfile, secretsfile, outputymlfile):
    replaced = replace_secrets_in_file(ymlfile, secretsfile)
    with open(outputymlfile, "w") as file:
        file.write(replaced)

def replace_secrets_in_file(source_file, secret_file):
    secrets = read_env_file(secret_file)
    with open(source_file, 'r') as file:
        content = file.read()
    for key, value in secrets.items():
        placeholder = f"${key}"
        content = content.replace(placeholder, value)
    return content

def main():
    args = parse_arguments()

    # Determine the manager IP
    if args.manager == 'auto':
        manager_ip = get_manager_ip()
        args.manager = f'ubuntu@{manager_ip}'

    if not file_exists(args.project):
        print(f'The yml file for the project "{args.project}" does not exist.', file=sys.stderr)
        sys.exit(1)
    if not os.path.isfile(f'./secrets/{args.project}.secrets'):
        print(f'The secrets file for the project "{args.project}" does not exist.', file=sys.stderr)
        sys.exit(1)

    try:
        ecr_uri = get_ecr_uri()  # Dynamically fetch ECR URI
        replace_secrets(f'./docker-swarm/{args.project}.yml', f'./secrets/{args.project}.secrets', f'./secrets/{args.project}.yml')
        ecr_login(args.manager, args.key, ecr_uri)
        sync_files(args.project, args.manager, args.key)
        deploy_stack(args.project, args.manager, args.key)
        print(f'Project {args.project} deployed successfully!')
    except subprocess.CalledProcessError as e:
        print(f'An error occurred: {e}', file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
