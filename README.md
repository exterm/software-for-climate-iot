# IOT grid dashboard code

## Developing

Look at the [Makefile](Makefile) for common development tasks.

### Circup

For managing the circuitpython dependencies on the device, you will need [circup](https://github.com/adafruit/circup).

The easiest way to install it is via `pip install circup`. If you're using the `asdf` version manager, you'll have to `asdf reshim python` to add the executable to your path.

### Screen (`make shell`)

We're using `screen` to open a shell to the device. Quitting the shell is counter-intuitive.
`Ctrl-D` will execute a soft restart of the device. To quit the shell, you can use `Ctrl-A k` and confirm with `y`.
