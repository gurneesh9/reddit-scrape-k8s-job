from kubernetes import client, config, utils
import time
from jinja2 import Template

def create_config_from_template(subreddit):
    template_content = open('scrape-job.yaml.template', 'r')
    template = Template(template_content.read())
    print(template)
    rendered_template = template.render(subreddit=subreddit)
    with open(f'scrape-job-{subreddit}.yaml', 'w') as f:
        f.write(rendered_template)

    return f'scrape-job-{subreddit}.yaml'

def run(k8s_manifest):
    config.load_kube_config()
    k8s_client = client.ApiClient()
    yaml_file = k8s_manifest
    utils.create_from_yaml(k8s_client, yaml_file, verbose=True)

def delete_jobs(k8s_manifest):
    config.load_kube_config()
    batch_v1_api = client.BatchV1Api()
    
    # Parse the YAML file
    with open(k8s_manifest, 'r') as file:
        resources = utils.parse_yaml(file.read())
    
    # Ensure resources are a list for multi-document YAML
    if not isinstance(resources, list):
        resources = [resources]
    
    # Iterate through the resources and delete Jobs
    for resource in resources:
        kind = resource.get("kind")
        metadata = resource.get("metadata", {})
        name = metadata.get("name")
        namespace = metadata.get("namespace", "default")  # Default namespace
        
        if kind == "Job":
            print(f"Deleting Job '{name}' in namespace '{namespace}'...")
            try:
                batch_v1_api.delete_namespaced_job(
                    name=name, 
                    namespace=namespace, 
                    body=client.V1DeleteOptions(propagation_policy="Foreground")
                )
                print(f"Job '{name}' deleted successfully.")
            except client.exceptions.ApiException as e:
                print(f"Failed to delete Job '{name}': {e}")


if __name__ == '__main__':
    subreddit = 'wallpapers'
    file_name = create_config_from_template(subreddit)
    run(file_name)
    print("Waiting for 20 sec")
    time.sleep(20)
    delete_jobs(file_name)
