class ServiceLayout:
    def __init__(self, services_on_all_hosts=[], service_counts={}, services_on_remaining_hosts=[]):
        """
        Service Layout describing layout of heterogeneous services in a
        Couchbase cluster.
        Some services may run on all nodes.
        Some services may run on N nodes.
        Some services may run on (Total Nodes) - N nodes (remaining node)
        services_on_all_hosts should be subset list of ["data", "fts", "query", "index"]
        service_counts should be something like
        {"data": 3}. Don't include a service in both args.
        """
        for s in services_on_all_hosts:
            if s in service_counts:
                raise Exception("Do not include a service in both services_on_all_hosts and service_counts args.")

        self.services_on_all_hosts = services_on_all_hosts
        self.service_counts = service_counts
        self.services_on_remaining_hosts = services_on_remaining_hosts

    def __str__(self) -> str:
        return (
            f"ServiceLayout(all_nodes={self.services_on_all_hosts}"
            f"n_nodes={self.service_counts},remaining_nodes={self.services_on_remaining_hosts})"
        )

    def get_simple_name(self):
        fname = (
            f'ALL{"-".join(self.services_on_all_hosts)}-'
        )
        for s, count in self.service_counts.items():
            fname += (
                f'{count}{s}'
            )
        fname += (
            f'REMAINING{"-".join(self.services_on_remaining_hosts)}'
        )
        return fname
