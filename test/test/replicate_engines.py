#!/usr/bin/env python

import os
import replicate
from mysql.utilities.exception import MySQLUtilError, MUTException

class test(replicate.test):
    """setup replication
    This test attempts to replicate among a master and slave whose
    innodb settings are different. It uses the replicate test for
    inherited methods.
    """

    def check_prerequisites(self):
        if self.servers.get_server(0).check_version_compat(5, 5, 0):
            raise MUTException("Test requires server version 5.1.")
        return self.check_num_servers(1)

    def setup(self):
        self.server0 = self.servers.get_server(0)
        self.server3 = None
        self.server2 = None
        self.server4 = None
        self.s1_serverid = None
        self.s2_serverid = None
        self.s3_serverid = None
        self.s4_serverid = None

        replicate.test.setup(self)
        
        index = self.servers.find_server_by_name("rep_slave_missing_engines")
        if index >= 0:
            self.server3 = self.servers.get_server(index)
            try:
                res = self.server3.show_server_variable("server_id")
            except MySQLUtilError, e:
                raise MUTException("Cannot get replication slave " +
                                   "server_id: %s" % e.errmsg)
            self.s3_serverid = int(res[0][1])
        else:
            self.s3_serverid = self.servers.get_next_id()
            res = self.servers.spawn_new_server(self.server0, self.s3_serverid,
                                                "rep_slave_missing_engines",
                                              ' --mysqld="--log-bin=mysql-bin '
                                         '--default_storage_engine=blackhole"')
            if not res:
                raise MUTException("Cannot spawn replication slave server.")
            self.server3 = res[0]
            self.servers.add_new_server(self.server3, True)
            
        index = self.servers.find_server_by_name("rep_master_missing_engines")
        if index >= 0:
            self.server4 = self.servers.get_server(index)
            try:
                res = self.server4.show_server_variable("server_id")
            except MySQLUtilError, e:
                raise MUTException("Cannot get replication master " +
                                   "server_id: %s" % e.errmsg)
            self.s4_serverid = int(res[0][1])
        else:
            self.s4_serverid = self.servers.get_next_id()
            res = self.servers.spawn_new_server(self.server0, self.s4_serverid,
                                               "rep_master_missing_engines",
                                              ' --mysqld="--log-bin=mysql-bin '
                                            '--default_storage_engine=memory"')
            if not res:
                raise MUTException("Cannot spawn replication slave server.")
            self.server4 = res[0]
            self.servers.add_new_server(self.server4, True)

        return True
    
    def run_test_case(self, slave, master, s_id,
                      comment, options=None, expected_result=0):
        
        master_str = "--master=%s" % self.build_connection_string(master)
        slave_str = " --slave=%s" % self.build_connection_string(slave)
        conn_str = master_str + slave_str
        
        # Test case 1 - setup replication among two servers
        self.results.append(comment+"\n")
        cmd = "mysqlreplicate.py -vvv --rpl-user=rpl:rpl %s" % conn_str
        if options:
            cmd += " %s" % options
        res = self.exec_util(cmd, self.res_fname)
        self.record_results(self.res_fname)
        if res != expected_result:
            return False

        return True
    
    def run(self):
        self.res_fname = self.testdir + "result.txt"
        
        comment = "Test case 1 - show warnings if slave has different " \
                  "default engines"
        res = self.run_test_case(self.server3, self.server2, self.s3_serverid,
                                 comment, None)
        if not res:
            raise MUTException("%s: failed" % comment)
        
        comment = "Test case 2 - use pedantic to fail if slave has " \
                  "different default engines"
        res = self.run_test_case(self.server3, self.server2, self.s3_serverid,
                                 comment, " --pedantic", 1)
        if not res:
            raise MUTException("%s: failed" % comment)

        try:
            res = self.server3.exec_query("STOP SLAVE")
        except:
            raise MUTException("%s: Failed to stop slave." % comment)


        comment = "Test case 3 - show warnings if master has different " \
                  "default engines"
        res = self.run_test_case(self.server1, self.server4, self.s1_serverid,
                                 comment, None)
        if not res:
            raise MUTException("%s: failed" % comment)
        
        comment = "Test case 4 - use pedantic to fail if master has " \
                  "different default engines"
        res = self.run_test_case(self.server1, self.server4, self.s1_serverid,
                                 comment, " --pedantic", 1)
        if not res:
            raise MUTException("%s: failed" % comment)

        try:
            res = self.server1.exec_query("STOP SLAVE")
        except:
            raise MUTException("%s: Failed to stop slave." % comment)

        replicate.test.mask_results(self)
        
        return True

    def get_result(self):
        return self.compare(__name__, self.results)
    
    def record(self):
        return self.save_result_file(__name__, self.results)
    
    def cleanup(self):
        if self.res_fname:
            os.unlink(self.res_fname)
        return True

