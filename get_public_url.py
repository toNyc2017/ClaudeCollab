import boto3

def get_public_url():
    # Initialize ECS, ELBv2, and EC2 clients
    ecs_client = boto3.client('ecs')
    elbv2_client = boto3.client('elbv2')
    ec2_client = boto3.client('ec2')
    
    try:
        # Step 1: List all ECS clusters
        clusters_response = ecs_client.list_clusters()
        clusters = clusters_response.get('clusterArns', [])
        
        if not clusters:
            return "No ECS clusters found."
        
        print(f"Found Clusters: {clusters}")
        cluster_name = clusters[0]  # Use the first cluster
        print(f"Using Cluster: {cluster_name}")
        
        # Step 2: List all services in the cluster
        services_response = ecs_client.list_services(cluster=cluster_name)
        services = services_response.get('serviceArns', [])
        
        if not services:
            return f"No services found in cluster {cluster_name}."
        
        print(f"Found Services: {services}")
        
        # Find the claude-service
        claude_service = None
        for service in services:
            if 'claude-service' in service:
                claude_service = service
                break
                
        if not claude_service:
            return "Claude service not found in the cluster."
            
        service_name = claude_service
        print(f"Using Service: {service_name}")
        
        # Step 3: Describe the selected ECS service
        service_response = ecs_client.describe_services(
            cluster=cluster_name,
            services=[service_name]
        )
        service = service_response['services'][0]
        
        # Step 4: Check for Load Balancer
        if 'loadBalancers' in service and service['loadBalancers']:
            load_balancer_name = service['loadBalancers'][0]['loadBalancerName']
            lb_response = elbv2_client.describe_load_balancers(
                Names=[load_balancer_name]
            )
            dns_name = lb_response['LoadBalancers'][0]['DNSName']
            return f"Load Balancer DNS: http://{dns_name}"
        
        # Step 5: If no Load Balancer, check for public IP of tasks
        elif 'networkConfiguration' in service:
            # List tasks for the service
            task_response = ecs_client.list_tasks(
                cluster=cluster_name,
                serviceName=service_name
            )
            task_arns = task_response.get('taskArns', [])
            
            if not task_arns:
                return "No running tasks found for the service."
            
            # Describe the tasks
            task_details = ecs_client.describe_tasks(
                cluster=cluster_name,
                tasks=task_arns
            )
            
            eni_ids = []
            for task in task_details['tasks']:
                for attachment in task['attachments']:
                    for detail in attachment['details']:
                        if detail['name'] == 'networkInterfaceId':
                            eni_ids.append(detail['value'])
            
            if not eni_ids:
                return "No network interfaces found for tasks."
            
            # Get public IPs for ENIs
            eni_response = ec2_client.describe_network_interfaces(
                NetworkInterfaceIds=eni_ids
            )
            
            public_ips = [
                eni['Association']['PublicIp']
                for eni in eni_response['NetworkInterfaces']
                if 'Association' in eni and 'PublicIp' in eni['Association']
            ]
            
            if public_ips:
                return f"Public IPs: {', '.join([f'http://{ip}:8000' for ip in public_ips])}"  # Added port 8000
            else:
                return "No public IPs found for tasks."
        
        else:
            return "The service is not exposed via a load balancer or public IP."
    
    except Exception as e:
        return f"Error: {str(e)}"

# Main function
if __name__ == "__main__":
    print("Starting script to find public URL or IP of ECS Fargate service...")
    public_url = get_public_url()
    print(public_url)