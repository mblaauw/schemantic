# Hosting the booking service: options (fictional)

We looked at virtual machines, Kubernetes and serverless, on four things.

Peak load: VMs cannot scale fast enough for the Monday peak. Kubernetes scales in about a minute, which is enough.
Serverless scales immediately.

Run cost: VMs are cheap to run at steady load but we pay for idle nights. Kubernetes is middling; we already have a cluster.
Serverless is the cheapest for this pattern, by our estimate.

Team skills: everyone knows VMs. Half the team knows Kubernetes. Nobody has run serverless in production.

Lock-in: VMs and Kubernetes move anywhere. Serverless ties us to the provider.

Our recommendation is Kubernetes: it is fast enough, we have the cluster, and half the team knows it.
