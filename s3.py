#!/usr/bin/env python

## Amazon S3 manager
## Author: Michal Ludvig <michal@logix.cz>
##         http://www.logix.cz/michal
## License: GPL Version 2

import sys
import logging
import time

from optparse import OptionParser
from logging import debug, info, warning, error
import elementtree.ElementTree as ET

## Our modules
from S3.S3 import *

def output(message):
	print message

def cmd_buckets_list_all(args):
	s3 = S3(AwsConfig())
	response = s3.list_all_buckets()

	for bucket in response["list"]:
		output("%s  %s" % (
			formatDateTime(bucket["CreationDate"]),
			s3.compose_uri(bucket["Name"]),
			))

def cmd_buckets_list_all_all(args):
	s3 = S3(AwsConfig())
	response = s3.list_all_buckets()

	for bucket in response["list"]:
		cmd_bucket_list([bucket["Name"]])
		output("")


def cmd_bucket_list(args):
	s3 = S3(AwsConfig())
	isuri, bucket, object = s3.parse_s3_uri(args[0])
	if not isuri:
		bucket = args[0]
	output("Bucket '%s':" % bucket)
	try:
		response = s3.bucket_list(bucket)
	except S3Error, e:
		if S3.codes.has_key(e.Code):
			error(S3.codes[e.Code] % bucket)
			return
		else:
			raise
	for object in response["list"]:
		size, size_coeff = formatSize(object["Size"], AwsConfig.human_readable_sizes)
		output("%s  %s%s  %s" % (
			formatDateTime(object["LastModified"]),
			str(size).rjust(8), size_coeff.ljust(1),
			s3.compose_uri(bucket, object["Key"]),
			))

def cmd_bucket_create(args):
	s3 = S3(AwsConfig())
	isuri, bucket, object = s3.parse_s3_uri(args[0])
	if not isuri:
		bucket = args[0]
	try:
		response = s3.bucket_create(bucket)
	except S3Error, e:
		if S3.codes.has_key(e.Code):
			error(S3.codes[e.Code] % bucket)
			return
		else:
			raise
	output("Bucket '%s' created" % bucket)

def cmd_bucket_delete(args):
	s3 = S3(AwsConfig())
	isuri, bucket, object = s3.parse_s3_uri(args[0])
	if not isuri:
		bucket = args[0]
	try:
		response = s3.bucket_delete(bucket)
	except S3Error, e:
		if S3.codes.has_key(e.Code):
			error(S3.codes[e.Code] % bucket)
			return
		else:
			raise
	output("Bucket '%s' removed" % bucket)

def cmd_object_put(args):
	s3 = S3(AwsConfig())

	s3uri = args.pop()
	files = args[:]

	isuri, bucket, object = s3.parse_s3_uri(s3uri)
	if not isuri:
		raise ParameterError("Expecting S3 URI instead of '%s'" % s3uri)

	if len(files) > 1 and object != "" and not AwsConfig.force:
		error("When uploading multiple files the last argument must")
		error("be a S3 URI specifying just the bucket name")
		error("WITHOUT object name!")
		error("Alternatively use --force argument and the specified")
		error("object name will be prefixed to all stored filanames.")
		exit(1)

	for file in files:
		if len(files) > 1:
			object_final = object + os.path.basename(file)
		elif object == "":
			object_final = os.path.basename(file)
		else:
			object_final = object
		response = s3.object_put(file, bucket, object_final)
		output("File '%s' stored as %s (%d bytes)" %
			(file, s3.compose_uri(bucket, object_final), response["size"]))

def cmd_object_get(args):
	s3 = S3(AwsConfig())
	s3uri = args.pop(0)
	isuri, bucket, object = s3.parse_s3_uri(s3uri)
	if not isuri or not bucket or not object:
		raise ParameterError("Expecting S3 object URI instead of '%s'" % s3uri)
	destination = len(args) > 0 and args.pop(0) or object
	if os.path.isdir(destination):
		destination += ("/" + object)
	if not AwsConfig.force and os.path.exists(destination):
		raise ParameterError("File %s already exists. Use --force to overwrite it" % destination)
	response = s3.object_get(destination, bucket, object)
	output("Object %s saved as '%s' (%d bytes)" %
		(s3uri, destination, response["size"]))

def cmd_object_del(args):
	s3 = S3(AwsConfig())
	s3uri = args.pop(0)
	isuri, bucket, object = s3.parse_s3_uri(s3uri)
	if not isuri or not bucket or not object:
		raise ParameterError("Expecting S3 object URI instead of '%s'" % s3uri)
	response = s3.object_delete(bucket, object)
	output("Object %s deleted" % s3uri)

commands = {
	"lb" : ("List all buckets", cmd_buckets_list_all, 0),
	"cb" : ("Create bucket", cmd_bucket_create, 1),
	"mb" : ("Create bucket", cmd_bucket_create, 1),
	"rb" : ("Remove bucket", cmd_bucket_delete, 1),
	"db" : ("Remove bucket", cmd_bucket_delete, 1),
	"ls" : ("List objects in bucket", cmd_bucket_list, 1),
	"la" : ("List all object in all buckets", cmd_buckets_list_all_all, 0),
	"put": ("Put file into bucket", cmd_object_put, 2),
	"get": ("Get file from bucket", cmd_object_get, 1),
	"del": ("Delete file from bucket", cmd_object_del, 1),
	}

if __name__ == '__main__':
	if float("%d.%d" %(sys.version_info[0], sys.version_info[1])) < 2.5:
		sys.stderr.write("ERROR: Python 2.5 or higher required, sorry.\n")
		exit(1)

	default_verbosity = AwsConfig.verbosity
	optparser = OptionParser()
	optparser.set_defaults(config=os.getenv("HOME")+"/.s3cfg")
	optparser.add_option("-c", "--config", dest="config", metavar="FILE", help="Config file name")
	optparser.set_defaults(verbosity = default_verbosity)
	optparser.add_option("-d", "--debug", dest="verbosity", action="store_const", const=logging.DEBUG, help="Enable debug output")
	optparser.add_option("-v", "--verbose", dest="verbosity", action="store_const", const=logging.INFO, help="Enable verbose output")
	optparser.set_defaults(human_readable = False)
	optparser.add_option("-H", "--human-readable", dest="human_readable", action="store_true", help="Print sizes in human readable form")
	optparser.set_defaults(force = False)
	optparser.add_option("-f", "--force", dest="force", action="store_true", help="Force overwrite and other dangerous operations")
	optparser.set_defaults(show_uri = False)
	optparser.add_option("-u", "--show-uri", dest="show_uri", action="store_true", help="Show complete S3 URI in listings")

	(options, args) = optparser.parse_args()

	## Some mucking with logging levels to enable 
	## debugging/verbose output for config file parser on request
	logging.basicConfig(level=options.verbosity, format='%(levelname)s: %(message)s')
	
	## Now finally parse the config file
	AwsConfig(options.config)

	## And again some logging level adjustments
	## according to configfile and command line parameters
	if options.verbosity != default_verbosity:
		AwsConfig.verbosity = options.verbosity
	logging.root.setLevel(AwsConfig.verbosity)

	## Update AwsConfig with other parameters
	AwsConfig.human_readable_sizes = options.human_readable
	AwsConfig.force = options.force
	AwsConfig.show_uri = options.show_uri

	if len(args) < 1:
		error("Missing command. Please run with --help for more information.")
		exit(1)

	command = args.pop(0)
	try:
		debug("Command: " + commands[command][0])
		## We must do this lookup in extra step to 
		## avoid catching all KeyError exceptions
		## from inner functions.
		cmd_func = commands[command][1]
	except KeyError, e:
		error("Invalid command: %s" % e)
		exit(1)

	if len(args) < commands[command][2]:
		error("Not enough paramters for command '%s'" % command)
		exit(1)

	try:
		cmd_func(args)
	except S3Error, e:
		error("S3 error: " + str(e))
	except ParameterError, e:
		error("Parameter problem: " + str(e))


