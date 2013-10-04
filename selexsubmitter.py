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
import re
import RNA

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

def writeToFreebase(cleanJson, aServiceUrl, anHttp, someCredentials):
  #create an empty selex experiment topic and get its mid
  mid_dict = createSelexExperimentTopic(aServiceUrl, anHttp, someCredentials)
  #add the reference details from this experiment
  addReferenceDetails(mid_dict, cleanJson, aServiceUrl, anHttp, someCredentials)
  addSelexDetails(mid_dict, cleanJson, aServiceUrl, anHttp, someCredentials)
  addSelexConditions(mid_dict, cleanJson, aServiceUrl, anHttp,someCredentials)
  addInteractions(mid_dict["mid"], cleanJson, aServiceUrl, anHttp, someCredentials)
  return mid_dict

#Creates a empty interaction topic including and returns the mid
# and connects it to the given selex experiment mid
def createInteractionTopic(aSelexExperimentMid, aServiceUrl, anHttp, someCredentials):
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

#creates an affinity conditions topic and its corresponding binding solution
# and connects it to the given affinity experiment mid and returns a dictionary of the mids
def createAffinityConditions(anAffinityExperimentMid, aServiceUrl, anHttp, someCredentials):
  rm = {}
  q = {
    "create":"unconditional",
    "mid":None,
    "type":"/base/aptamer/affinity_conditions",
    "b:type":"/base/aptamer/experimental_conditions",
    "/base/aptamer/experimental_conditions/are_experimental_conditions_of":{
      "connect":"insert",
      "mid":anAffinityExperimentMid
    }
  }
  params = makeRequestBody(someCredentials, q)
  aff_cond_mid = runQuery(params, aServiceUrl, anHttp)
  if aff_cond_mid == None:
    raise Exception("could not create affinity conditions!")
    sys.exit()
  else:
    rm["mid"] = aff_cond_mid
    #create a binding solution and attach it 
    q={
      "create":"unconditional",
      "mid":None,
      "type":"/base/aptamer/binding_solution",
      "/base/aptamer/binding_solution/is_binding_solution_of":{
        "connect":"insert",
        "mid": aff_cond_mid
      }
    }
    params = makeRequestBody(someCredentials, q)
    bs_mid = runQuery(params, aServiceUrl, anHttp)
    rm["binding_solution"] = bs_mid
    if bs_mid == None:
      raise Exception("Could not create bidning solution topic!")
      sys.exit()
    else:
      return rm

#creates an aptamer topic and connects it to the passed in interaction mid. 
#Uses the given aptamer type, mutational analysis and sequence
def createAptamerTopic(anInteractionMid, aType, aSequence, aServiceUrl, anHttp, someCredentials):
  seq_len = len(aSequence)
  at = ""
  if aType.lower() == "dna":
    at = "/base/aptamer/dna"
  if aType.lower() == "rna":
    at = "/base/aptamer/rna"
  if len(at):
    q = {
      "create":"unconditional",
      "mid":None,
      "type":"/base/aptamer/interactor",
      "b:type":"/base/aptamer/aptamer",
      "c:type":"/base/aptamer/linear_polymer",
      "d:type":"/chemistry/chemical_compound",
      "e:type":at,
      "f:type":"/base/aptamer/nucleic_acid",
      "/base/aptamer/interactor/is_participant_in":{
        "connect":"insert",
        "mid":anInteractionMid
      },
      "/base/aptamer/linear_polymer/sequence":{
        "connect":"insert",
        "value": aSequence
      },
      "/base/aptamer/linear_polymer/sequence_length":{
        "connect":"insert",
        "value":int(seq_len)
      }
    }
    p = makeRequestBody(someCredentials, q)
    r = runQuery(p, aServiceUrl, anHttp)
    if r == None:
      raise Exception("Could not create aptamer topic")
      sys.exit()
    else:
      return r
  else:
    raise Exception("Not a valid aptamer type was passed in")
    sys.exit()


#creates an aptamer target topic and connects it to a passed in interaction mid. Uses the given name aswell
def createAptamerTargetTopic(anInteractionMid, aTargetName,aTargetTypeMid,aServiceUrl,anHttp,someCredentials):
  q = {
    "create":"unconditional",
    "mid":None,
    "type":"/base/aptamer/interactor",
    "b:type":"/base/aptamer/aptamer_target",
    "c:type" :"/chemistry/chemical_compound",
    "/base/aptamer/interactor/is_participant_in":{
      "connect":"insert",
      "mid":anInteractionMid
    },
    "name":{
      "connect":"insert",
      "value" : str(aTargetName),
      "lang":"/lang/en"
    },
    "/base/aptamer/aptamer_target/has_type":{
      "connect":"insert",
      "mid":aTargetTypeMid
    }
  }
  p = makeRequestBody(someCredentials, q)
  r = runQuery(p, aServiceUrl, anHttp)
  if r == None:
    raise Exception("Could not create aptamer target topic")
    sys.exit()
  else:
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

#Create an empty floating point range topic 
def createFloatingPointRangeTopic(aKdMid, aServiceUrl, anHttp, someCredentials):
  q = {
    "create":"unconditional",
    "mid":None,
    "type":"/measurement_unit/floating_point_range"
  }
  p = makeRequestBody(someCredentials, q)
  fpr_mid = runQuery(p, aServiceUrl, anHttp)
  if fpr_mid == None:
    raise Exception("Could not create floating point range!")
    sys.exit()
  else:
    return fpr_mid
#creates a predicted secondary structure topic 
# adds the given dbn and mfe 
# assumes program used was RNAfold
def createPredictedSecondaryStructureTopic(apt_mid, dbn, mfe, aServiceUrl, anHttp, someCredentials):
  q = {
    "create":"unconditional",
    "mid":None,
    "type":"/base/aptamer/predicted_secondary_structure",
    "/base/aptamer/predicted_secondary_structure/software_used":{
      "connect":"insert",
      "mid":"/m/0gkkmsx"
    },
    "/base/aptamer/predicted_secondary_structure/dot_bracket_notation":{
      "connect":"insert",
      "value":str(dbn),
      "lang":"/lang/en"
    },
    "/base/aptamer/predicted_secondary_structure/minimum_free_energy":{
      "connect":"insert",
      "value":float(mfe)
    },
    "/base/aptamer/predicted_secondary_structure/is_predicted_secondary_structure_of":{
      "connect":"insert",
      "mid":apt_mid
    }
  }
  p = makeRequestBody(someCredentials, q)
  pss_mid = runQuery(p, aServiceUrl, anHttp)
  if pss_mid == None:
    raise Exception("Could not create predicted secondary structure topic!")
    sys.exit()
  else:
    return pss_mid

#creates an empty dissociation constant topic and returns it 
# atttaches it to the given affinity experiment mid
def createDissociationConstantTopic(aff_exp_mid, aServiceUrl, anHttp, someCredentials):
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
    sys.exit()
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
    return None

def addInteractions(aSelexExperimentMid,cleanJson, aServiceUrl, anHttp, someCredentials):
  #iterate over the interactions
  for ai in cleanJson["interactions"]:
    #create an empty interaction topic
    int_mid = createInteractionTopic(aSelexExperimentMid, aServiceUrl, anHttp, someCredentials)
    #now iterate over the affinity experiments in clean json
    for ae in ai["affinity_experiments"]:
      #create an empty affinity experiment topic
      aff_mid = createAffinityExperimentTopic(int_mid, aServiceUrl, anHttp, someCredentials)
      #create an empty kd topic
      kd_mid = createDissociationConstantTopic(aff_mid, aServiceUrl, anHttp, someCredentials)
      #add the value of the dissociation constant 
      #(add the value to temporary value as well)
      try:
        kd = ae["kd"]
        q={
          "mid":kd_mid,
          "/base/aptamer/dissociation_constant/has_value":{
            "connect":"insert",
            "value":float(kd),
          },
          "/base/aptamer/dissociation_constant/has_temporary_string_value":{
            "connect":"insert",
            "value" :str(kd),
            "lang":"/lang/en"
          },
          "/base/aptamer/dissociation_constant/is_dissociation_constant_of":{
            "connect":"insert",
            "mid":int_mid
          }
        }
        p = makeRequestBody(someCredentials, q)
        r = runQuery(p, aServiceUrl, anHttp)
        if r == None:
          raise Exception("Could not create kd topic!")
          sys.exit()
      except KeyError:
        pass
      #add the range of the dissociation constant
      try:
        kd_range_dirty = ae["kd_range"]
        #now split by " to "
        kd_range = kd_range_dirty.split(" to ")
        if len(kd_range) == 2:
          low =  kd_range[0]
          high = kd_range[1]
          #create a floating_point_range topic
          pfr_mid = createFloatingPointRangeTopic(kd_mid, aServiceUrl, anHttp, someCredentials)
          #add the values
          q = {
            "mid":pfr_mid,
            "/measurement_unit/floating_point_range/low_value":{
              "connect":"insert",
              "value":float(low)
            },
            "/measurement_unit/floating_point_range/high_value":{
              "connect":"insert",
              "value":float(high)
            }
          }
          p = makeRequestBody(someCredentials, q)
          r = runQuery(p, aServiceUrl, anHttp)
          if r == None:
            raise Exception("Could not create range topic")
            sys.exit()
          else:
            #connect the floating point range back to the kd topic
            q = {
              "mid":kd_mid,
              "/base/aptamer/dissociation_constant/has_value_range":{
                "connect":"insert",
                "mid":pfr_mid
              },
              "/base/aptamer/dissociation_constant/has_temporary_string_value_range":{
                "connect":"insert",
                "value":str(kd_range),
                "lang":"/lang/en"
              }
            }
            p = makeRequestBody(someCredentials, q)
            r = runQuery(p, aServiceUrl, anHttp)
            if r == None:
              raise Exception("Could not connect kd to range value")
              sys.exit()
      except KeyError:
        pass
      #add the error of the dissociation constant
      try:
        error = ae["kd_error"]
        q = {
          "mid":kd_mid,
          "/base/aptamer/dissociation_constant/has_error":{
            "connect":"insert",
            "value":float(error)
          },
          "/base/aptamer/dissociation_constant/temporary_error_string":{
            "connect":"insert",
            "value": error,
            "lang": "/lang/en"
          }
        }
        p = makeRequestBody(someCredentials, q)
        r = runQuery(p, aServiceUrl, anHttp)
        if r == None:
          raise Exception("Could not add kd error")
          sys.exit()
      except KeyError:
        pass
      #create an affinity conditions topic
      aff_cond_dict = createAffinityConditions(aff_mid, aServiceUrl, anHttp, someCredentials)
      #add the affinity experiment details
      #add the affinity method to the affinity experiment topic
      try:
        for afn in ae["affinity_methods_names"]:
          #affinity method
          q = {
            "mid": aff_mid,
            "/base/aptamer/affinity_experiment/affinity_method":{
              "connect":"insert",
              "name": str(afn),
              "type":"/base/aptamer/affinity_method"
            }
          }
          params = makeRequestBody(someCredentials, q)
          r = runQuery(params, aServiceUrl, anHttp)
          if r == None:
            raise Exception("Could not add affinity method "+ afn)
            sys.exit()
      except KeyError:
        pass
      #now add the affinity conditions for this experiment
      #first add the buffering agent for the binding solution of the affinity conditions
      try:
        for aba in ae["buffering_agent_names"]:
          q={
            "mid": aff_cond_dict["binding_solution"],
            "/base/aptamer/binding_solution/has_buffering_agent":{
              "connect":"insert",
              "name":str(aba),
              "type":"/base/aptamer/buffering_agent"
            }
          }
          params = makeRequestBody(someCredentials, q)
          r = runQuery(params, aServiceUrl, anHttp)
          if r == None:
            raise Exception ("Could not add buffering agent to binding solution")
            sys.exit()
      except KeyError:
        q = {
          "mid": aff_cond_dict["binding_solution"],
          "/base/aptamer/binding_solution/has_buffering_agent":{
            "connect":"insert",
            "mid":"/m/0g5m7lm"
          }
        }
        p = makeRequestBody(someCredentials, q)
        r = runQuery(p, aServiceUrl, anHttp)
        if r == None:
          raise Exception("Could not add buffering agent to binding solution! errono 99")
          sys.exit()   
      #now add the metal cation concentrations to the binding solution
      try:
        for amcc in ae["ae_metal_cation_concs"]:
          q={
            "mid":aff_cond_dict["binding_solution"],
            "/base/aptamer/binding_solution/ionic_strength":{
              "connect":"insert",
              "value":str(amcc),
              "lang": "/lang/en"
            }
          }
          params = makeRequestBody(someCredentials, q)
          r = runQuery(params, aServiceUrl, anHttp)
          if r == None:
            raise Exception ("Could not add ionic strength to binding solution!")
            sys.exit()
      except KeyError:
        pass
      #now add the ph to the binding solution
      try:
        ph = ae["ph"]
        q={
          "mid":aff_cond_dict["binding_solution"],
          "/base/aptamer/binding_solution/ph":{
            "connect":"insert",
            "value":float(ph)
          }
        }
        p = makeRequestBody(someCredentials, q)
        r = runQuery(p, aServiceUrl, anHttp)
        if r == None:
          raise Exception ("Could not add ph")
          sys.exit()
      except KeyError:
        pass
      #now add the temperature 
      try:
        temp = ae["temperature"]
        q = {
          "mid":aff_cond_dict["binding_solution"],
          "/base/aptamer/binding_solution/temperature":{
            "connect":"insert",
            "value":float(temp)
          }
        }
        p = makeRequestBody(someCredentials, q)
        r = runQuery(p, aServiceUrl, anHttp)
        if r == None:
          raise Exception ("Could not add temperature")
          sys.exit()
      except KeyError:
        pass
    #now find  the aptamer target name from the input
    aptamer_target_name = ai["aptamer_target"]["name"]
    #ask the user to identify the type of the target
    target_type_mid = promptUserForTargetType(aptamer_target_name)
    #create an aptamer target topic and add the passed in name
    att_mid = createAptamerTargetTopic(int_mid, aptamer_target_name, target_type_mid, aServiceUrl, anHttp, someCredentials)
    #now add the aptamers to the interaction
    try:
      for anApt in ai["aptamers"]:
        apt_mid = createAptamerTopic(int_mid, anApt["polymer_type"], anApt["sequence"], aServiceUrl, anHttp, someCredentials)
        #now predict the secondary structure
        fold = RNA.fold(str(anApt["sequence"]))
        dbn = fold[0]
        mfe = fold[1]
        #create a predicted secondary structure topic
        pred_ss_mid = createPredictedSecondaryStructureTopic(apt_mid, dbn, mfe, aServiceUrl, anHttp, someCredentials)
        #now add the mutational analysis to the aptamer topic
        try:
          ma = True
          if anApt["mutational_analysis"].lower() == "no":
            ma = False
          q={
            "mid":apt_mid,
            "/base/aptamer/aptamer/has_mutational_analysis":{
              "connect":"insert",
              "value": ma
            }
          }
          p = makeRequestBody(someCredentials, q)
          r = runQuery(p, aServiceUrl, anHttp)
          if r == None:
            raise Exception("Could not add mutational_analysis ")
            sys.exit()
        except KeyError:
          pass
        #now add the secondary structures 
        try:
          for ssn in anApt["secondary_structures_names"]:
            q={
              "mid":apt_mid,
              "/base/aptamer/nucleic_acid/secondary_structure":{
                "connect":"insert",
                "name": str(ssn),
                "type":"/base/aptamer/nucleic_acid_secondary_structure"
              }
            }
            p = makeRequestBody(someCredentials, q)
            r = runQuery(p, aServiceUrl, anHttp)
            if r == None:
              raise Exception("Could not add secondary strucutres")
              sys.exit()
        except KeyError:
          pass
        #now add the application
        try:
          q = {
            "mid":apt_mid,
            "/base/aptamer/application":{
              "connect":"insert",
              "value":str(anApt["application"]),
              "lang":"/lang/en"
            }
          }
          p = makeRequestBody(someCredentials, q)
          r = runQuery(p, aServiceUrl, anHttp)
          if r == None:
            raise Exception("Could not add application")
            sys.exit()
        except KeyError:
          pass
        #now add the sequence pattern
        try:
          q = {
            "mid":apt_mid,
            "/base/aptamer/linear_polymer/sequence_pattern":{
              "connect":"insert",
              "value":str(anApt["sequence_pattern"]),
              "lang":"/lang/en"
            }
          }
          p = makeRequestBody(someCredentials, q)
          r = runQuery(p, aServiceUrl, anHttp)
          if r == None:
            raise Exception("Could not add sequence pattern")
            sys.exit()
        except KeyError:
          pass
      #now add the collective or pairwise interaction type
      int_type = "/base/aptamer/pairwise_interaction"
      if len(ai["aptamers"]) > 1:
        int_type = "/base/aptamer/collective_interaction"
      q={
        "mid":int_mid,
        "type":{
          "connect":"insert",
          "id":int_type
        }
      }
      p = makeRequestBody(someCredentials, q)
      r = runQuery(p, aServiceUrl, anHttp)
      if r == None:
        raise Exception("Could not add intercaction type")
        sys.exit()
    except KeyError:
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
    var_region_summation = computeVariableRegionSummation(ts)
    if var_region_summation > 1:
      q ={
        "mid" : anMidDict["selex_conditions"],
        "/base/aptamer/selex_conditions/has_template_sequence":{
          "connect":"insert",
          "value":str(ts),
        },
        "/base/aptamer/selex_conditions/template_variable_region_summation":{
          "connect": "insert",
          "value": int(var_region_summation)
        }
      }
    else:
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
    q = {
    "mid": anMidDict["selection_solution"],
    "/base/aptamer/binding_solution/has_buffering_agent":{
      "connect":"insert",
      "mid":"/m/0g5m7lm"
      }
    }
    p = makeRequestBody(someCredentials, q)
    r = runQuery(p, aServiceUrl, anHttp)
    if r == None:
      raise Exception("Could not add buffering agent to binding solution! errono 99")
      sys.exit()
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
          "name": str(an),
          "type":"/base/aptamer/separation_methods"
        } 
      }
      params = makeRequestBody(someCredentials, q)
      if runQuery(params, aServiceUrl, anHttp) == None:
        raise Exception("Could not run query! 113")
        sys.exit()
  except KeyError:
    q = {
      "mid": anMidDict["partitioning_method"],
      "/base/aptamer/partitioning_method/has_separation_method":{
        "connect":"insert",
        "mid": "/m/0g5m7lm"
      }
    }
    p = makeRequestBody(someCredentials, q)
    if runQuery(p, aServiceUrl, anHttp) == None:
      raise Exception ("Could not add default partitioning_method")
      sys.exit()
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
    q ={
      "mid":anMidDict["recovery_method"],
      "/base/aptamer/recovery_method_se/has_recovery_method":{
        "connect":"insert",
        "mid":"/m/0g5m7lm"
      }
    }
    p = makeRequestBody(someCredentials, q)
    if runQuery(p, aServiceUrl, anHttp) == None:
      raise Exception("Could not add default recovery method!")
      sys.exit()

def computeVariableRegionSummation(aTemplateSequence):
   #compute the variable region summation 
    pat1 = '^NO\-TEMPLATE$'
    pat2 = '^[ACGTRUYKMSWBDHVNX-]+\s*-\s*(\d+)\s*-\s*[ACGTRUYKMSWBDHVNX-]+$'
    pat3 = '^[ACGTRUYKMSWBDHVNX-]+\s*-\s*(\d+)\s*-\s*[ACGTRUYKMSWBDHVNX-]+\s*-\s*(\d+)\s*-\s*[ACGTRUYKMSWBDHVNX-]+\s*$'
    m1 = re.match(pat1, aTemplateSequence)
    m2 = re.match(pat2, aTemplateSequence)
    m3 = re.match(pat3, aTemplateSequence)
    if m1:
      return -1
    elif m2:
      return float(m2.group(1))
    elif m3:
      r = float(m3.group(1)) + float(m3.group(2))
      return r
    else:
      return -1

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

#this method prompts the user to select the correct target type
# for the passed in target name. The options are: 1. cell, 2. small molecule 3. protein
# ask the user until they answer correctly
# returns the Mid of the type the user picked
def promptUserForTargetType(aTargetName):
  opts = "Please choose one of the following options that best describes the aptamer target : "+aTargetName+"\n"
  opts += "1 : cell\n2 : protein\n3 : small molecule\n"
  anMid = None
  x = 0
  while not x:
    try:
      choice = int(raw_input(opts))
      if choice == 1:
        x =1 
        return "/m/01cbd"
      elif choice == 2:
        x =1 
        return "/m/05wvs"
      elif choice == 3:
        x= 1
        return "/m/043tvww"
      else:
        print "invalid option... try again"   
    except ValueError, e:
      print ("'%s' is not a valid integer." % e.args[0].split(": ")[1])


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
