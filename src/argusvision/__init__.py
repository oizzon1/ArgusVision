"""ArgusVision — an aerial detection-to-segmentation platform.

The package is the platform: datasets, model adapters, the detect→segment
pipeline, the frozen evaluation stack, tiled inference, and the `argusvision`
command line. It carries nothing specific to one experiment.

Experiments live outside it, as YAML configs under `experiments/configs/`, and
write to `results/`. The dividing question for any new file is whether a
*different* experiment would need it: if yes it belongs in the package, if no
it is configuration.

    argusvision run experiments/configs/<config>.yaml
    argusvision status --watch

Thesis-era code is preserved on the `legacy_thesis` branch and at git tag
`thesis-code-final`; it is history, not a source.
"""

__version__ = "0.1.0"
