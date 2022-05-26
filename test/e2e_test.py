#!/usr/local/bin/python2

import os
import sys

import difflib

import configparser
import logging

EOL = "\n"

RELAY_SCRIPT = "test/relay.py"
CONFIG_FILE = "test/gpg-mailgate.conf"

PYTHON_BIN = "python2.7"

def build_config(config):
    cp = configparser.ConfigParser()

    cp.add_section("logging")
    cp.set("logging", "file", "/dev/stout")
    cp.set("logging", "verbose", "yes")

    cp.add_section("gpg")
    cp.set("gpg", "keyhome", config["gpg_keyhome"])

    cp.add_section("smime")
    cp.set("smime", "cert_path", config["smime_certpath"])

    cp.add_section("relay")
    cp.set("relay", "host", "localhost")
    cp.set("relay", "port", config["port"])

    logging.debug("Created config with keyhome=%s, cert_path=%s and relay at port %d" %
                  (config["gpg_keyhome"], config["smime_certpath"], config["port"]))
    return cp

def write_test_config(outfile, **config):
    logging.debug("Generating configuration with %s" % repr(config))

    out = open(outfile, "w+")
    cp = build_config(config)
    cp.write(out)
    out.close()

    logging.debug("Wrote configuration to %s" % outfile)

def load_file(name):
	f = open(name, 'r')
	contents = f.read()
	f.close()

	return contents

def strip_eols(strings):
    return [s.strip("\r") for s in strings]

def compare(result, expected):
    result_lines = strip_eols(result.split(EOL))
    expected_lines = strip_eols(expected.split(EOL))

    return difflib.unified_diff(expected_lines, result_lines,
                                fromfile='expected',
                                tofile='output')

def report_result(message_file, expected_file, test_output):
    expected = load_file(expected_file)
    diff = compare(test_output, expected)
    if len(list(diff)) > 0:
        print("Output and the expected message (%s) don't match:" % (expected_file))
    else:
        print("Message %s processed properly" % (message_file))
    for diff_line in diff:
        print(diff_line)

def execute_e2e_test(message_file, expected_file, **kwargs):
    test_command = "%s gpg-mailgate.py %s < %s" % (PYTHON_BIN, kwargs["from_addr"], message_file)
    result_command = "%s %s %d" % (PYTHON_BIN, RELAY_SCRIPT, kwargs["port"])

    logging.debug("Spawning: '%s'" % (result_command))
    pipe = os.popen(result_command, 'r')

    logging.debug("Spawning: '%s'" % (test_command))
    msgin = os.popen(test_command, 'w')
    msgin.write(load_file(message_file))
    msgin.close()

    testout = pipe.read()
    pipe.close()

    logging.debug("Read %d characters of test output: '%s'" % (len(testout), testout))

    report_result(message_file, expected_file, testout)

def load_config():
    cp = configparser.ConfigParser()
    cp.read("test/e2e.ini")

    return cp


config = load_config()

logging.basicConfig(filename	= "e2e_test.log",
                    format		= "%(pathname)s:%(lineno)d %(levelname)s [%(funcName)s] %(message)s",
                    datefmt		= "%Y-%m-%d %H:%M:%S",
                    level		= logging.DEBUG)

write_test_config(os.getcwd() + "/" + CONFIG_FILE,
                  port				= config.getint("relay", "port"),
                  gpg_keyhome		= "test/keyhome",
                  smime_certpath	= "test/certs")

for case_no in range(1, config.getint("tests", "cases")+1):
    case_name = "case-%d" % (case_no)

    execute_e2e_test(config.get(case_name, "in"), config.get(case_name, "out"),
                    from_addr	= config.get(case_name, "from"),
                    port		= config.getint("relay", "port"))
