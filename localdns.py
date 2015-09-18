import re

class LocalDNS(object):
    def list_records(self):
        """
        List all records in the dns
        """
        pass

    def add_record(self, domain, ip):
        """
        Add a new record to the dns
        """
        pass

    def remove_record(self, domain):
        """
        Remove a record from the dns
        """
        pass

    def contains_record(self, domain):
        """
        :return: if the given domain exists in the dns records
        """
        pass


class MemoryLocalDNS(LocalDNS):
    def __init__(self, *args, **kwargs):
        super(MemoryLocalDNS, self).__init__(*args, **kwargs)

        self.records = {}

    def list_records(self):
        return list(self.records.iteritems())

    def add_record(self, domain, ip):
        self.records[domain] = ip

    def remove_record(self, domain):
        del self.records

    def contains_record(self, domain):
        return domain in self.records


class HostsLocalDNS(MemoryLocalDNS):
    def __init__(self, *args, **kwargs):
        super(HostsLocalDNS, self).__init__(*args, **kwargs)
        self.load_hosts()

    def load_hosts(self):
        hosts_file = open('/etc/hosts')

        for line in hosts_file.readlines():
            if line.strip().startswith("#"):
                continue
            parts = line.split(' ')
            if len(parts) < 2:
                continue
            if re.match('^\d+[.]\d+[.]\d+[.]\d+$', parts[0].strip()):
                self.add_record(parts[1].strip(), parts[0].strip())
        hosts_file.close()

    def save_hosts(self):
        hosts_file = open('/etc/hosts', 'w')
        hosts_file.write('\n'.join(map(lambda (x, y): y + " " + x, self.list_records())))
        hosts_file.close()

    def add_record(self, *args, **kwargs):
        super(HostsLocalDNS, self).add_record(*args, **kwargs)
        self.save_hosts()

    def remove_record(self, *args, **kwargs):
        super(HostsLocalDNS, self).remove_record(*args, **kwargs)
        self.save_hosts()


local_dns = HostsLocalDNS()


def list_records():
    return local_dns.list_records()


def add_record(domain, ip):
    return local_dns.add_record(domain, ip)


def remove_record(domain):
    return local_dns.remove_record(domain)


def contains_record(domain):
    return local_dns.contains_record(domain)