# -*- coding: utf-8 -*-
# Copyright (c) 2013 Jose Cruz-Toledo

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

#
# Copyright (C) 2013 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Command-line skeleton application for Freebase API.
Usage:
  $ python selexsubmitter.py

You can also get help on all the command-line flags the program understands
by running:

  $ python selexsubmitter.py --help

"""

import argparse
import httplib2
import os
import sys
import json
import urllib
import os.path
import pprint

from pprint import pprint
from urllib import urlencode
from apiclient import discovery
from oauth2client import file
from oauth2client import client
from oauth2client import tools

# Parser for command-line arguments.
parser = argparse.ArgumentParser(
    description=__doc__,
    formatter_class=argparse.RawDescriptionHelpFormatter,
    parents=[tools.argparser])
parser.add_argument('-su', '--servlet_url', help='the URL of the servlet that parses the JSON files', required=True)
parser.add_argument('-dir', '--input_directory', help='the local directory that has the input JSON files', required=True)

# CLIENT_SECRETS is name of a file containing the OAuth 2.0 information for this
# application, including client_id and client_secret. You can see the Client ID
# and Client secret on the APIs page in the Cloud Console:
# <https://cloud.google.com/console#/project/1083819269171/apiui>
CLIENT_SECRETS = os.path.join(os.path.dirname(__file__), 'client_secrets.json')

# Set up a Flow object to be used for authentication.
# Add one or more of the following scopes. PLEASE ONLY ADD THE SCOPES YOU
# NEED. For more information on using scopes please see
# <https://developers.google.com/+/best-practices>.
FLOW = client.flow_from_clientsecrets(CLIENT_SECRETS,
  scope=[
      'https://www.googleapis.com/auth/freebase',
    ],
    message=tools.message_if_missing(CLIENT_SECRETS))


def main(argv):
  # Parse the command-line flags.
  flags = parser.parse_args(argv[1:])
  #define some vars 
  service_url_write = 'https://www.googleapis.com/freebase/v1sandbox/mqlwrite'
  inputFilesPath = flags.input_directory
  servlet_url = flags.servlet_url

  # If the credentials don't exist or are invalid run through the native client
  # flow. The Storage object will ensure that if successful the good
  # credentials will get written back to the file.
  storage = file.Storage('sample.dat')
  credentials = storage.get()
  if credentials is None or credentials.invalid:
    credentials = tools.run_flow(FLOW, storage, flags)

  # Create an httplib2.Http object to handle our HTTP requests and authorize it
  # with our good Credentials.
  http = httplib2.Http()
  http = credentials.authorize(http)
  # Construct the service object for the interacting with the Freebase API.
  service = discovery.build('freebase', 'v1', http=http)
  for fn in os.listdir(inputFilesPath):
    if fn:
      cleanJson = getCleanJson(servlet_url, inputFilesPath ,fn)
      #now prepare a write query for the cleanJSON
      se_mid = writeToFreebase(cleanJson, service_url_write, http, credentials)
      print se_mid
      sys.exit()
    
#Creates a empty interaction topic including and returns the mid
def createInteractionTopic(aSelexExperimentMid, aServiceUrl, anHttp, someCredentials):
  rm = {}
  q = {
    "create":"unconditional",
    "mid":None,
    "type":"/base/aptamer/interaction",
    "b:type":"/base/aptamer/experimental_outcome",
    "/base/aptamer/experimental_outcome/is_outcome_of":{
      "connect":"insert",
      "mid" : aSelexExperimentMid
    }
  }
  params = makeRequestBody(someCredentials, q)
  r = runQuery(params, aServiceUrl, anHttp)
  if r == None:
    raise Exception ("Could not create interaction topic!")
    sys.exit()
  return r
  
#Creates an empty affinityExperiment topic and returs its mid
# attaches the created topic to the given interaction topic mid
def createAffinityExperimentTopic(anInteractionMid, aServiceUrl, anHttp, someCredentials):
  q={
    "create":"unconditional",
    "mid":None,
    "type":"/base/aptamer/affinity_experiment",
    "b:type":"/base/aptamer/experiment",
    "/base/aptamer/affinity_experiment/confirms":{
      "connect":"insert",
      "mid":anInteractionMid
    }
  }
  params = makeRequestBody(someCredentials, q)
  afe_mid = runQuery(params, aServiceUrl, anHttp)
  if afe_mid == None:
    raise Exception("Could not create affinity experiment!")
    sys.exit()
  else:
    return afe_mid
  # if afe_mid:
  #   rm["mid"] = afe_mid
  #   #now create a kd topic
  #   q={
  #     "create":"unconditional",
  #     "mid":None,
  #     "type":"/base/aptamer/dissociation_constant",
  #     "b:type":"/base/aptamer/experimental_outcome",
  #     "/base/aptamer/experimental_outcome/is_outcome_of":{
  #       "connect":"insert",
  #       "mid":afe_mid
  #     }
  #   }
  #   params = makeRequestBody(someCredentials, q)
  #   kd_mid = runQuery(params, aServiceUrl, anHttp)
  #   if kd_mid == None:
  #     raise Exception ("Could not create kd!")
  #   if kd_mid:
  #     rm["kd_mid"] = kd_mid
  #     #connect the kd to the affinity expeirment
  #     q={
  #       "mid":afe_mid,
  #       "/base/aptamer/experiment/has_outcome":{
  #         "connect":"insert",
  #         "mid" : kd_mid,
  #       }
  #     }
  #     params = makeRequestBody(someCredentials, q)
  #     runQuery(params, aServiceUrl, anHttp)
  #     #connect the kd back to the interaction
  #     q = {
  #       "mid":kd_mid,
  #       "/base/aptamer/dissociation_constant/is_dissociation_constant_of":{
  #         "connect":"insert",
  #         "mid": anInteractionMid
  #       }
  #     }
  #     params = makeRequestBody(someCredentials, q)
  #     runQuery(params, aServiceUrl, anHttp)

#creates an empty dissociation constant topic and returns it 
# atttaches it to the given affinity experiment mid
def createDissociationConstantTopic(aff_exp_mid, ServiceUrl, anHttp, someCredentials):
  q = {
    "create":"unconditional",
    "mid":None,
    "type":"/base/aptamer/dissociation_constant",
    "b:type":"/base/aptamer/experimental_outcome",
    "/base/aptamer/experimental_outcome/is_outcome_of":{
      "connect":"insert",
      "mid":aff_exp_mid
    }
  }
  params = makeRequestBody(someCredentials, q)
  kd_mid = runQuery(params, aServiceUrl, anHttp)
  if kd_mid == None:
    raise Exception("Cannot create kd topic!")
    sys.exit()
  else:
    return kd_mid
  

#Creates an empty selex experiment topic
#creates the corresponding topics:
# partitioning method, recovery methods and selex conditions
#returns a dictionary with mids for all its parts
def createSelexExperimentTopic(aServiceUrl, anHttp, someCredentials):
  rm = {}
  #1: create a selex experiment topic
  q = {
    "create" :"unconditional",
    "mid" : None,
    "type" : "/base/aptamer/selex_experiment",
    "b:type" : "/base/aptamer/experiment",
    "c:type" : "/base/aptamer/interaction_experiment",
  }
  params = makeRequestBody(someCredentials, q)
  se_mid = runQuery(params, aServiceUrl, anHttp)
  if se_mid:
    rm["mid"]= se_mid
    #now create the partitioning and recovery methods and attach them 
    #to the selex experiment topic created earlier
    #create a partitioning method topic
    q = {
      "create" :"unconditional",
      "mid":None,
      "type":"/base/aptamer/partitioning_method",
      "/base/aptamer/partitioning_method/is_partitioning_method_of":{"connect":"insert", "mid":se_mid}
    }
    params = makeRequestBody(someCredentials, q)
    pm_mid = runQuery(params, aServiceUrl, anHttp)
    rm["partitioning_method"] = pm_mid
    #create a recovery method topic
    q = {
      "create":"unconditional", "mid":None, 
      "type":"/base/aptamer/recovery_method_se",
      "/base/aptamer/recovery_method_se/is_recovery_method_of":{"connect":"insert", "mid":se_mid}
    }
    params = makeRequestBody(someCredentials, q)
    rm_mid = runQuery(params, aServiceUrl, anHttp)
    rm["recovery_method"] = rm_mid
    #create an empty selex condition topic
    q = {
      "create":"unconditional", "mid":None,
      "type":"/base/aptamer/selex_conditions",
      "b:type": "/base/aptamer/experimental_conditions",
      "/base/aptamer/experimental_conditions/are_experimental_conditions_of":{"connect":"insert", "mid":se_mid}
    }
    params = makeRequestBody(someCredentials, q)
    sc_mid = runQuery(params, aServiceUrl, anHttp)
    rm["selex_conditions"] = sc_mid
    if sc_mid:
      #create a selection solution and attach it to the selex conditions topic
      q = {
        "create":"unconditional", "mid":None, 
        "type":"/base/aptamer/selection_solution",
        "/base/aptamer/selection_solution/is_selection_solution_of_sc":{"connect":"insert", "mid":sc_mid}
      }
      params = makeRequestBody(someCredentials, q)
      ss_mid = runQuery(params, aServiceUrl, anHttp)
      rm["selection_solution"] = ss_mid
      if not ss_mid:
        raise Exception ("Could not create selection solution!")
        sys.exit()
    else:
      raise Exception("Could not create selex conditions!")
      sys.exit()
    
    return rm
  else:
    raise Exception("Could not create Selex experiment topic!")
    return None;

def makeRequestBody(someCredentials, aQuery):
  p ={
    'oauth_token': someCredentials.access_token,
    'query': json.dumps(aQuery)
  }
  return p

def runQuery(someParams, aServiceUrl, anHttp):
  url = aServiceUrl+'?'+urllib.urlencode(someParams)
  resp, content = anHttp.request(url)
  if resp["status"] == '200':
    #everything worked
    r = json.loads(content)
    return r["result"]["mid"]
  else:
    print someParams
    print resp
    print content
    raise Exception("Could not run query!! erno:234442")
    sys.exit()
    return None

def writeToFreebase(cleanJson, aServiceUrl, anHttp, someCredentials):

  #create an empty selex experiment topic and get its mid
  mid_dict = createSelexExperimentTopic(aServiceUrl, anHttp, someCredentials)
  #add the reference details from this experiment
  addReferenceDetails(mid_dict, cleanJson, aServiceUrl, anHttp, someCredentials)
  addSelexDetails(mid_dict, cleanJson, aServiceUrl, anHttp, someCredentials)
  addSelexConditions(mid_dict, cleanJson, aServiceUrl, anHttp,someCredentials)
  addInteractions(mid_dict, cleanJson, aServiceUrl, anHttp, someCredentials)
  return mid_dict


def addInteractions(anMidDict,cleanJson, aServiceUrl, anHttp, someCredentials):
  #iterate over the interactions
  for ai in cleanJson["interactions"]:
    #create an empty interaction topic
    int_mid = createInteractionTopic(anMidDict["mid"], aServiceUrl, anHttp, someCredentials)
    #now iterate over the affinity experiments in clean json
    for ae in ai["affinity_experiments"]:
      #create an empty affinity experiment topic
      aff_mid = createAffinityExperimentTopic(int_mid, aServiceUrl, anHttp, someCredentials)
      afe = cleanJson["intercations"]
  pass

# add the follwing details:
# number of rounds
# template sequence
# template bias
# has template bias
# selection solution
def addSelexConditions(anMidDict, cleanJson, aServiceUrl, anHttp, someCredentials):
  #add the number of rounds
  try:
    nor = cleanJson["se"]["selex_conditions"]["numOfSelectionRounds"]
    q = {
      "mid": anMidDict["selex_conditions"],
      "/base/aptamer/selex_conditions/number_of_selection_rounds": {
        "connect":"insert",
        "value":int(nor)
      }
    }
    params = makeRequestBody(someCredentials, q)
    if runQuery(params, aServiceUrl, anHttp) == None:
      raise Exception ("Could not run query! 9984")
      sys.exit()
  except KeyError:
    pass
  #add the template sequence
  try:
    ts = cleanJson["se"]["selex_conditions"]["template_sequence"]
    q = {
      "mid" : anMidDict["selex_conditions"],
      "/base/aptamer/selex_conditions/has_template_sequence":{
        "connect":"insert",
        "value":str(ts)
      }
    }
    params = makeRequestBody(someCredentials, q)
    if runQuery(params, aServiceUrl, anHttp) == None:
      raise Exception ("Could not run query! 99843234")
      sys.exit()
  except KeyError:
    pass
  #add the template bias
  try:
    tb = cleanJson["se"]["selex_conditions"]["template_bias"]
    tb_bool = False
    if tb.lower == "yes":
      tb_bool = True
    q = {
      "mid" : anMidDict["selex_conditions"],
      "/base/aptamer/selex_conditions/has_template_bias":{
        "connect":"insert",
        "value": tb_bool
      }
    }
    params = makeRequestBody(someCredentials, q)
    if runQuery(params, aServiceUrl, anHttp) == None:
      raise Exception ("Could not run query! 4830943")
      sys.exit()
  except KeyError:
    pass
  #add the selection solution's ph
  try:
    ph = cleanJson["se"]["selex_conditions"]["ph"]
    q = {
      "mid":anMidDict["selection_solution"],
      "/base/aptamer/selection_solution/ph":{
        "connect":"insert",
        "value": float(ph)
      }
    }
    params = makeRequestBody(someCredentials, q)
    if runQuery(params, aServiceUrl, anHttp) == None:
      raise Exception ("Could not run query! 4830943")
      sys.exit()
  except KeyError:
    pass
  #add the selection solution's temperature
  try:
    temp = cleanJson["se"]["selex_conditions"]["temperature"]
    q = {
      "mid":anMidDict["selection_solution"],
      "/base/aptamer/selection_solution/temperature":{
        "connect":"insert",
        "value":float(temp)
      }
    }
    params = makeRequestBody(someCredentials, q)
    if runQuery(params, aServiceUrl, anHttp) == None:
      raise Exception ("Could not run query! 43543543")
      sys.exit()
  except KeyError:
    pass
  #add the selection solution's buffering agents
  try:
    ba = cleanJson["se"]["selex_conditions"]["buffering_agents"]
    for aba in ba:
      q = {
        "mid":anMidDict["selection_solution"],
        "/base/aptamer/selection_solution/has_buffering_agent":{
          "connect":"insert",
          "name": aba,
          "type":"/base/aptamer/buffering_agent"
        }
      }
      params = makeRequestBody(someCredentials, q)
      if runQuery(params, aServiceUrl, anHttp) == None:
        raise Exception ("Could not run query! 98327492387423")
        sys.exit()
  except KeyError:
    pass
  #add the selection solution's metal cation conc string
  try:
    mcc = cleanJson["se"]["selex_conditions"]["metal_cation_concentration"]
    for amcc in mcc:
      q = {
        "mid":anMidDict["selection_solution"],
        "/base/aptamer/selection_solution/ionic_strength":{
          "connect":"insert",
          "value":str(amcc),
          "lang": "/lang/en"
        }
      }
      params = makeRequestBody(someCredentials, q)
      if runQuery(params, aServiceUrl, anHttp) == None:
        raise Exception ("Could not run query! 98327492387423")
        sys.exit()
  except KeyError:
    pass
#add the following details:
# partitioning method
# recovery method
# selex method
def addSelexDetails(anMidDict, cleanJson, aServiceUrl, anHttp, someCredentials):
  #add the selex method
  try:
    sm = cleanJson["se"]["selex_methods"]
    for asm in sm:
      q = {
        "mid": anMidDict["mid"],
        "/base/aptamer/selex_experiment/has_selex_method":{
          "connect":"insert",
          "name": str(asm),
          "type":"/base/aptamer/selex_method"
        }
      }
      params = makeRequestBody(someCredentials, q)
      if runQuery(params, aServiceUrl, anHttp) == None:
        raise Exception("Could not run query! 500-3")
        sys.exit()
  except KeyError:
    pass
  #now add the partitioning method
  try:
    pm_names = cleanJson["se"]["partitioning_methods"]
    for an in pm_names:
      q = {
        "mid": anMidDict["partitioning_method"],
        "/base/aptamer/partitioning_method/has_separation_method":{
          "connect":"insert",
          "name": an,
          "type":"/base/aptamer/separation_methods"
        } 
      }
      params = makeRequestBody(someCredentials, q)
      if runQuery(params, aServiceUrl, anHttp) == None:
        raise Exception("Could not run query! 113")
        sys.exit()
  except KeyError:
    pass
  #now add the recovery methods
  try:
    rm_names = cleanJson["se"]["recovery_methods"]
    for an in rm_names:
      q ={
        "mid": anMidDict["recovery_method"],
        "/base/aptamer/recovery_method_se/has_recovery_method":{
          "connect":"insert",
          "name":an,
          "type":"/base/aptamer/recovery_methods"
          }
      }
      p = makeRequestBody(someCredentials, q)
      if runQuery(p, aServiceUrl, anHttp) == None:
        raise Exception("Could not run query! 324")
        sys.exit()
  except KeyError:
    pass

#add the reference details to the anMid's selex experiment topic
# details to be added here are:
#   pmid, doi or reference string
def addReferenceDetails(anMidDict, cleanJson, aServiceUrl, anHttp, someCredentials):
  #first try the pmid
  try:
    pmid = cleanJson["se"]["pmid"]
    q = {
      "mid":anMidDict["mid"],
      "/base/aptamer/experiment/pubmed_id":{
        "connect":"insert",
        "value":str(pmid)
      }
    }
    params = makeRequestBody(someCredentials, q)
    if runQuery(params, aServiceUrl, anHttp) == None:
      raise Exception ("Could not run query! #2433211.3")
      sys.exit()
  except KeyError:
    pass
  #now try the doi
  try:
    doi = cleanJson["se"]["doi"]
    q = {
      "mid":anMidDict["mid"],
      "/base/aptamer/experiment/digital_object_identifier":{
        "connect":"insert",
        "value":str(doi)
      }
    }
    params = makeRequestBody(someCredentials, q)
    if runQuery(params, aServiceUrl, anHttp) == None:
      raise Exception("Could not run query! oi42h")
      sys.exit()
  except KeyError:
    pass
  #now try the reference
  try:
    reference = cleanJson["se"]["reference"]
    q = {
      "mid":anMidDict["mid"],
      "/base/aptamer/experiment/has_bibliographic_reference":{
        "connect":"insert",
        "value":str(reference)
      }
    }
    params = makeRequestBody(someCredentials, q)
    if runQuery(params, aServiceUrl, anHttp) == None:
      raise Exception("Could not run query! #dslkfj")
      sys.exit()
  except KeyError:
    pass

#This function calls the java servlet that parses the output of selexsubmit form
def getCleanJson(aServletUrl, aDirPath,aFileName):
  json_raw = open(aDirPath+'/'+aFileName, 'r')
  for aline in json_raw:
    fchar = aline[0]
    if fchar == '{':
      data = json.loads(aline)
      if data:
        print 'processing ' + aFileName + '...'
        #prepare the query
        params = {
          "se" : aline,
          "fn" : aDirPath+'/'+aFileName
        }
        #now call the servlet
        f = urllib.urlopen(aServletUrl, urlencode(params))
        output = f.read().replace("\\\"", "")
        if output:
          json_raw.close()
          rm = json.loads(output)
          return rm
        else:
          json_raw.close()
          raise Exception("Servlet found here: "+aServletUrl+" did not respond!")
          return None
    else:
      continue

if __name__ == '__main__':
  main(sys.argv)
