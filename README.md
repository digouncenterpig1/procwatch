# procwatch

Lightweight CLI daemon that monitors and restarts failing processes with configurable backoff strategies.

## Installation

```bash
pip install procwatch
```

Or install from source:

```bash
git clone https://github.com/youruser/procwatch.git && cd procwatch && pip install .
```

## Usage

Define your processes in a `procwatch.yaml` config file:

```yaml
processes:
  web-server:
    command: "python app.py"
    backoff: exponential
    max_retries: 5
    delay: 2

  worker:
    command: "celery -A tasks worker"
    backoff: linear
    max_retries: 10
    delay: 1
```

Start the daemon:

```bash
procwatch start --config procwatch.yaml
```

Check status of monitored processes:

```bash
procwatch status
```

Stop the daemon:

```bash
procwatch stop
```

### Backoff Strategies

| Strategy      | Description                              |
|---------------|------------------------------------------|
| `constant`    | Fixed delay between restarts             |
| `linear`      | Delay increases linearly with each retry |
| `exponential` | Delay doubles with each retry            |

## License

MIT © 2024