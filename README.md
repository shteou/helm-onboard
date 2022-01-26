# helm onboard

`helm onboard` converts a set of resources that have been applied to a namespace and
converts them to a bone fide helm release. This may be useful if the resources
were applied directly, or via helm template (with kubectl), or when switching from
an alternate tool like Kustomize.

## Usage

Let's assume you have a chart, `my-chart`, which has been installed with
`helm template importme my-chart | kubectl apply -f -` into the `default`
namespace.

We can onboard these resources by running the following command:

```bash
$ ./onboard default importme my-chart
```

## How does it work?

`helm onboard` starts by templating the provided chart and sanity checking
that those resources exist in the target namespace (these are presented as
warnings).

A new empty helm release is created (this is because the helm chart cannot
be installed over the existing resources, but can be upgraded), then the
existing resources are patched to indicate helm's ownership.

Finally the helm chart is upgraded. You can now deploy the helm chart
to deploy new versions of the software.

## Limitations

* Helm charts which span multiple namespaces might be problematic
* No attempt is made to detect resources outside of the scope of
  the supplied chart
