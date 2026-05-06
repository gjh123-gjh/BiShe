import pkg_resources

for dist in pkg_resources.working_set:
    try:
        dist.version
    except Exception as e:
        print(f"Error in {dist.project_name}: {e}")
    if "unsupported" in str(dist.version):
        print(f"Found problematic package: {dist.project_name} version {dist.version}")
