#!/usr/bin/env python3

import argparse, os, shutil, subprocess, sys, yaml
from os import error


def does_release_exist(release_name):
  result = subprocess.Popen(["kubectl", "get", "secret", f"sh.helm.release.v1.{release_name}.v1"], stdout=subprocess.PIPE)
  _ = result.communicate()[0]
  return result.returncode == 0


def does_resource_exist(resource):
  kind = resource["kind"]
  name = resource["metadata"]["name"]
  print(f"\tChecking for existence of {kind}/{name}")

  result = subprocess.Popen(["kubectl", "get", kind, name, "-o", "json"], stdout=subprocess.PIPE)

  # Note, the returncode is set as a result of calling communicate
  # This is a bit of a nasty hack, and should switch to wait() or something
  _ = result.communicate()[0]
  return_code = result.returncode

  if return_code == 0:
    print(f"\tFound {kind}/{name}\n")
  else:
    print(f"\tFailed to find {kind}/{name}\n")
  return return_code == 0

def change_namespace(namespace):
  result = subprocess.Popen(["jx", "namespace", namespace], stdout=subprocess.PIPE)
  _ = result.communicate()[0]
  return result.returncode == 0


def create_empty_helm_chart():
  print("Creating empty helm chart")
  result = subprocess.Popen(["helm", "create", "empty"], stdout=subprocess.PIPE)
  _ = result.communicate()[0]
  if result.returncode != 0:
    print("Error!")
    return False

  try:
    shutil.rmtree(os.path.join("empty", "templates"))
  except OSError as err:
    print("Error2!", err)
    return False
  return True

# Installs the empty chart with the given release name
def install_empty_helm_chart(release_name):
  result = subprocess.Popen(["helm", "install", release_name, "empty"], stdout=subprocess.PIPE)
  _ = result.communicate()[0]

  if result.returncode != 0:
    return False
  return True

def template_chart(release_name, chart_name):
  result = subprocess.Popen(["helm", "template", release_name, chart_name], stdout=subprocess.PIPE)
  response = result.communicate()[0]

  if result.returncode != 0:
    return None
  else:
    return response


# Creates an empty helm release
def create_empty_helm_release(release_name):
  if not create_empty_helm_chart():
    return False

  return install_empty_helm_chart(release_name)

def patch_resource(resource, release_name, namespace):
  kind = resource["kind"]
  name = resource["metadata"]["name"]

  print(f"Annotating {kind}/{name} with release name")
  result = subprocess.Popen(["kubectl", "annotate", kind, name, f"meta.helm.sh/release-name={release_name}"], stdout=subprocess.PIPE)
  _ = result.communicate()[0]

  if result.returncode != 0:
    return False

  print(f"Annotating {kind}/{name} with release namespace")
  result = subprocess.Popen(["kubectl", "annotate", kind, name, f"meta.helm.sh/release-namespace={namespace}"], stdout=subprocess.PIPE)
  _ = result.communicate()[0]

  if result.returncode != 0:
    return False

  print(f"Annotating {kind}/{name} with ManagedBy")
  result = subprocess.Popen(["kubectl", "label", kind, name, "app.kubernetes.io/managed-by=Helm"], stdout=subprocess.PIPE)
  _ = result.communicate()[0]
  return result.returncode == 0


def patch_resources(resources, release_name, namespace):
  print("Patching resources")
  print(resources)
  for r in resources:
    print("Patching a resource")
    res = patch_resource(r, release_name, namespace)
    if not res:
      print("Warning: failed to patch resource!")

def upgrade_helm(release_name, chart_name):
  result = subprocess.Popen(["helm", "upgrade", release_name, chart_name], stdout=subprocess.PIPE)
  _ = result.communicate()[0]
  if result.returncode != 0:
    return False

if __name__ == "__main__":
  parser = argparse.ArgumentParser(description='onboard resources into helm!')
  parser.add_argument("namespace", type=str,
                      help="The helm release's namespace, e.g. default")
  parser.add_argument("release_name", type=str,
                      help="The name of the helm release, e.g. release")
  parser.add_argument("chart_name", type=str,
                      help="The (directory) name of the helm chart to be installed")

  args = parser.parse_args()
  namespace = args.namespace
  release_name = args.release_name
  chart_name = args.chart_name

  print(f"Switching namespace to {namespace}")
  change_namespace(namespace)


  # Check if the release exists already
  print("Loading expected resources")
  resources_string = template_chart(release_name, chart_name)
  if resources_string == None:
    print("Failed to template provided chart, exiting")
    sys.exit(1)
  
  resources = []
  for r in yaml.safe_load_all(resources_string):
    resources.append(r)

  print("Checking resources exist")
  applied_statuses = list(map(does_resource_exist, resources))

  if not all(applied_statuses):
    print("Warning: Helm deployment contains resources not already applied")
    print("Do you want to continue? [y/N]")
    should_continue = input()
    if should_continue != "y":
      sys.exit(1)
  

  print("Checking if release already exists")  
  if not does_release_exist(release_name):
    print("Creating an empty helm release")
    result = create_empty_helm_release(release_name)
    if result:
      print("Successfully created empty helm release")
    else:
      print("Failed to create empty helm release")
      sys.exit(1)
  else:
    print("Release already exists. Nothing to do.")
    sys.exit(0)

  print("Patching resources ready for helm upgrade")
  success = patch_resources(resources, release_name, namespace)
  if success:
    print("Successfully patched all resources")
  
  if upgrade_helm(release_name, chart_name):
    print(f"Successfully onboarded the helm chart {chart_name}")
  else:
    print(f"Failed to upgrade the helm release with the helm chart {chart_name}")
