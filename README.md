# helm2play
Use Helm charts for podman kube play

Enable and start podman API service

```
systemctl enable podman --now
```

Usage: helm2play.py [OPTIONS] [VALUES]

Options:
  --chart TEXT  Chart name  [required]
  --repo TEXT   Chart repo  [required]
  --name TEXT   Release name  [required]
  --help        Show this message and exit.


Example:

```
helm2play.py --chart superset --repo "http://apache.github.io/superset/" --name pk-superset ./values.yaml
```

It will generate __almost__ working manifest. You will to make a few fixes. You can do it manually or write a simple script. For example, for Apache Superset you can find it in fixes/superset.py
