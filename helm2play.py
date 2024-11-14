#!/usr/bin/env python3

import asyncio
import podman
from pyhelm3 import Client
import ruamel.yaml
import click

TEMPLATE_PVC = """
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  annotations:
    volume.podman.io/driver: local
  name:
spec:
"""
TEMPLATE_DEPLOYMENT = """
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name:
  labels:
spec:
  replicas:
  selector:
    matchLabels:
      app: 
      release: 
  template:
    metadata:
      annotations:
      labels:
        app:
        release:
    spec:
      securityContext:
        runAsUser:
      initContainers: []
      containers: []
      volumes: []
"""


PODMAN_SUPPORTED_KINDS = {
    "4.9": [
        'Pod',
        'Deployment',
        'PersistentVolumeClaim',
        'ConfigMap',
        'Secret',
        'DaemonSet'
    ]
}

def normalize(d):
    LT = ruamel.yaml.scalarstring.LiteralScalarString
    S = ruamel.yaml.scalarstring.DoubleQuotedScalarString
    if isinstance(d, dict):
        for k, v in d.items():
             d[k] = normalize(v)
        return d
    if isinstance(d, list):
        for idx, elem in enumerate(d):
            d[idx] = normalize(elem)
        return d
    if d in ['yes', 'no', 'true', 'false', 'on', 'off']:
        return S(d)
    if not isinstance(d, str):
        return d
    if '\n' in d:
        if isinstance(d, LT):
            return d     # already a block style literal scalar
        return LT(d)
    return str(d)

def get_supported_kinds():
    client = podman.PodmanClient(base_url='unix:///run/podman/podman.sock')
    if client.ping():
        info=client.info()
        ver = info['version']['Version']
    versions = PODMAN_SUPPORTED_KINDS.keys()
    supported = []
    for v in versions:
        if ver.startswith(v):
            supported.append(v)
        else:
            print("unsupported podman version")
    return PODMAN_SUPPORTED_KINDS[max(supported, key=len)]


async def get_template(chart: str, repo: str, name: str, values: dict):
    client = Client()
    c = await client.get_chart(
        chart,
        repo=repo
    )
    return list(await client.template_resources(
        c,
        name,
        values
    ))

def sort_kinds(template: list, kinds: list):
    supported = []
    unsupported = []
    for manifest in template:
        if manifest['kind'] in kinds:
            supported = supported + [normalize(manifest)]
        else:
            unsupported = unsupported + [normalize(manifest)]

    return supported, unsupported


def _vct2pvc(vct: dict):
    pvc = ruamel.yaml.safe_load(TEMPLATE_PVC)
    pvc['metadata'] = vct['metadata']
    pvc['spec'] = vct['spec']
    return pvc

def convert_sts(sts: list):
    res = []
    for s in sts:
        d = s
        d['kind'] = 'Deployment'
        vols = d['spec']['template']['spec'].pop('volumes')
        for p in d['spec'].pop('volumeClaimTemplates', []):
            res = res + [_vct2pvc(p)]
            vols = vols + [
                {
                    'name': p['metadata']['name'],
                    'persistentVolumeClaim': {
                        'name': p['metadata']['name']
                    }
                }
            ]
        d['spec']['template']['spec']['volumes'] = vols
        res = res + [d]
    return(res)

@click.command()
@click.option('--chart', help='Chart name', required=True, type=str)
@click.option('--repo', help='Chart repo', required=True, type=str)
@click.option('--name', help='Release name', required=True, type=str)
@click.argument('values', type=click.Path(exists=True), required=False)
def main(chart, repo, name, values):
    with open(values) as val_file:
        vals = ruamel.yaml.safe_load(val_file)
    template = loop.run_until_complete(get_template(
        chart=chart,
        repo=repo,
        name=name,
        values=vals
    ))
    print(f'Found {len(template)} original manifests')
    podman_play, unsupported = sort_kinds(template, get_supported_kinds())
    print(f'{len(podman_play)} supported manifests')
    print(f'{len(unsupported)} unsupported manifests')
    sts = convert_sts([sts for sts in unsupported if sts['kind'] == 'StatefulSet'])
    print(f'{len(sts)} converted to deployments')
    yaml = ruamel.yaml.YAML()
    with open(f'play-{name}.yaml', 'w') as play:
        yaml.dump_all(
                podman_play + sts,
                play
        )

if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    main()