#!/usr/bin/env python3

# To run Apache Superset manifest generated from Helm chart by helm2play
# we need some fixes
# 1. We need to fix redis and postgres hostnames in *-env secret
# 2. Fix deployments order in the manifest due to Podman inability to run 
# multiple deployments simultaneously
# 3. Publish port of Superset itself

import ruamel.yaml
import click
from pathlib import Path

@click.command()
@click.argument('manifest', type=click.Path(exists=True), required=False)
def main(manifest):
    yaml = ruamel.yaml.YAML()
    with open(manifest) as m:
        superset = list(yaml.load_all(m))

    cm = [cm for cm in superset if cm['kind'] == 'ConfigMap']
    secret = [s for s in superset if s['kind'] == 'Secret']
    deployments = [d for d in superset if d['kind'] in ['Deployment', 'Pod']]
    postgres = [p for p in deployments if p['metadata']['name'].endswith('-postgresql')][0]
    deployments.remove(postgres)
    name = postgres['metadata']['labels']['app.kubernetes.io/instance']
    superset_db_host = f"{postgres['metadata']['name']}-pod"
    redis = [r for r in deployments if '-redis' in r['metadata']['name']][0]
    deployments.remove(redis)
    superset_redis_host = f"{redis['metadata']['name']}-pod"
    superset_secret = [s for s in secret if s['metadata']['name'] == f'{name}-env'][0]
    secret.remove(superset_secret)
    superset_secret['stringData']['REDIS_HOST'] = superset_redis_host
    superset_secret['stringData']['DB_HOST'] = superset_db_host
    superset_pod = [p for p in deployments if p['metadata']['name'] == name][0]
    superset_pod['spec']['template']['spec']['containers'][0]['ports'][0]['hostPort'] = superset_pod['spec']['template']['spec']['containers'][0]['ports'][0]['containerPort']

    with open(f'{Path(manifest).stem}_fixed.yaml', 'w') as m:
        yaml.dump_all(
            cm +
            [superset_secret] +
            secret + 
            [redis, postgres] +
            deployments,
            m
        )

if __name__ == '__main__':
    main()