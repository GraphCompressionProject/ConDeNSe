import config;
import mdl_base;
import mdl_structs;
import mdl_error;
from copy import deepcopy;

from math import log,factorial;
from error import Error;
from graph import Graph;
from model import Model;

from mdl_base import *;
from mdl_structs import *;
from mdl_error import *;


### Our Encoding Starts Here ###

### Total Encoded Size
def L(G, M, errorEnc): 
    E = Error(G); # initially, everything is error, nothing is covered
    error_cost = 0;
    repeatedEdges = 0;
    repeatedErrors = 0;
   

    model_cost = LN(M.numStructs+1);    # encode number of structures we're encoding with
    model_cost += LwC(M.numStructs, M.numStrucTypes);            # encode the number per structure

    # encode the structure-type identifier per type
    if M.numFullCliques > 0 :
        model_cost += M.numFullCliques * log(M.numFullCliques / float(M.numStructs), 2);
    if M.numNearCliques  > 0 :
        model_cost += M.numNearCliques * log(M.numNearCliques / float(M.numStructs), 2);
    if M.numChains > 0 :
        model_cost += M.numChains * log(M.numChains / float(M.numStructs), 2);
    if M.numStars > 0 :
        model_cost += M.numStars * log(M.numStars / float(M.numStructs), 2);
    # off-diagonals
    if M.numFullOffDiagonals > 0 :
        model_cost += M.numFullOffDiagonals * log(M.numFullOffDiagonals / float(M.numStructs), 2);
    if M.numNearOffDiagonals > 0 :
        model_cost += M.numNearOffDiagonals * log(M.numNearOffDiagonals / float(M.numStructs), 2);
    # bipartite-cores
    if M.numBiPartiteCores > 0 :
        model_cost += M.numBiPartiteCores * log(M.numBiPartiteCores / float(M.numStructs), 2);
    if M.numNearBiPartiteCores > 0 :
        model_cost += M.numNearBiPartiteCores * log(M.numNearBiPartiteCores / float(M.numStructs), 2);
    if M.numJellyFishes > 0 :
        model_cost += M.numJellyFishes * log(M.numJellyFishes / float(M.numStructs), 2);
    if M.numCorePeripheries > 0 :
        model_cost += M.numCorePeripheries * log(M.numCorePeripheries / float(M.numStructs), 2);

    # encode the structures
    for struc in M.structs :
        if struc.isFullClique() :
            (cost,repeatedEdges,repeatedErrors) = LfullClique(struc,M,G,E);
            model_cost += cost;
        elif struc.isNearClique() :
            (cost,repeatedEdges,repeatedErrors) = LnearClique(struc,M,G,E);
            model_cost += cost;
        elif struc.isChain() :
            (cost,repeatedEdges,repeatedErrors) = Lchain(struc,M,G,E);
            model_cost += cost;
        elif struc.isStar() :
            (cost,repeatedEdges,repeatedErrors) = Lstar(struc,M,G,E);
            model_cost += cost;
        elif struc.isCorePeriphery() :
            (cost,repeatedEdges,repeatedErrors) = LcorePeriphery(struc,M,G,E);
            model_cost += cost;
        elif struc.isJellyFish() :
            (cost,repeatedEdges,repeatedErrors) = LjellyFish(struc,M,G,E);
            model_cost += cost;
        elif struc.isBiPartiteCore() :
            (cost,repeatedEdges,repeatedErrors) = LbiPartiteCore(struc,M,G,E);
            model_cost += cost;
        elif struc.isNearBiPartiteCore() :
            (cost,repeatedEdges,repeatedErrors) = LnearBiPartiteCore(struc,M,G,E);
            model_cost += cost;
        elif struc.isFullOffDiagonal() :
            (cost,repeatedEdges,repeatedErrors) = LfullOffDiagonal(struc,M,G,E);
            model_cost += cost;
        elif struc.isNearOffDiagonal() :
            (cost,repeatedEdges,repeatedErrors) = LnearOffDiagonal(struc,M,G,E);
            model_cost += cost;
    
    # encode the error
    error_cost += 0 if E.numCellsCovered == 0 else log(E.numCellsCovered, 2);    # encode number of additive Errors
    if ((G.numNodes * G.numNodes - G.numNodes) / 2) - E.numCellsCovered > 0 :
        error_cost += log(((G.numNodes * G.numNodes - G.numNodes) / 2) - E.numCellsCovered, 2);    # encode number of Errors
        
    if errorEnc == "NP" :
        error_cost += LErrorNaivePrefix(G,M,E);
    elif errorEnc == "NB" :
        error_cost += LErrorNaiveBinom(G,M,E);
    elif errorEnc == "TP" :
        error_cost += LErrorTypedPrefix(G,M,E);
    elif errorEnc == "TB" :
        error_cost += LErrorTypedBinom(G,M,E);
    
    total_cost = model_cost + error_cost;
    # Minimize error and increase coverage
    #if (G.numEdges - E.numUnmodelledErrors) > 0:
    total_cost_coverage = 1.0 * total_cost / (G.numEdges - E.numUnmodelledErrors + 1);
    # Minimize error and increase NEW coverage
    # Note: in this case the (NEW coverage) == coverage, since old coverage was 0
    total_cost_NEWcoverage = 1.0 * total_cost / (G.numEdges - E.numUnmodelledErrors + 1);
    total_cost_coverageRepeatedErr = 1.0 * total_cost * (repeatedEdges + 1) / (G.numEdges - E.numUnmodelledErrors + 1);
    total_cost_coverageRepeatedAll = 1.0 * total_cost * (repeatedErrors + repeatedEdges + 1) / (G.numEdges - E.numUnmodelledErrors + 1);
    
    #else:
    #    total_cost_coverage = 
    #    total_cost_NEWcoverage =     

    return (total_cost, model_cost, error_cost, E, total_cost_coverage, total_cost_NEWcoverage, total_cost_coverageRepeatedErr, total_cost_coverageRepeatedAll);

    
    
### Total Encoded Size for the greedy heuristic -- incrementally update the MDL cost
## for the newly added stucture 'struc'
def Lgreedy(G, M, errorEnc, time, struc, totalCostOld, Eold, model_cost_struct): 

    toKeep = 'true';
    old_numUnmodelledErrors = Eold.numUnmodelledErrors;
    if time == 1:
        E = Error(G); # initially, everything is error, nothing is covered
        #E.saveOld();
        # the cost for encoding each structure (to avoid recomputing it for the greedy updates)
        model_cost2 = 0;
    else :
        E = Eold; #Error(G, Eold);
        # clear the temp vars that keep the diff in the Error by adding the new structure
        E.resetLast();
        #E.deepish_copy(Eold);
        #E = copy.deepcopy(Eold);
        #E = Eold;
        # the cost for encoding each structure separately 
        # Just update the up-to-now cost by adding the cost of the new structure
        model_cost2 = model_cost_struct;

    error_cost = 0;
    repeatedEdges = 0;
    repeatedErrors = 0;
    

    model_cost = LN(M.numStructs+1);    # encode number of structures we're encoding with
    model_cost += LwC(M.numStructs, M.numStrucTypes);            # encode the number per structure

    # encode the structure-type identifier per type
    if M.numFullCliques > 0 :
        model_cost += M.numFullCliques * log(M.numFullCliques / float(M.numStructs), 2);
    if M.numNearCliques  > 0 :
        model_cost += M.numNearCliques * log(M.numNearCliques / float(M.numStructs), 2);
    if M.numChains > 0 :
        model_cost += M.numChains * log(M.numChains / float(M.numStructs), 2);
    if M.numStars > 0 :
        model_cost += M.numStars * log(M.numStars / float(M.numStructs), 2);
    # off-diagonals
    if M.numFullOffDiagonals > 0 :
        model_cost += M.numFullOffDiagonals * log(M.numFullOffDiagonals / float(M.numStructs), 2);
    if M.numNearOffDiagonals > 0 :
        model_cost += M.numNearOffDiagonals * log(M.numNearOffDiagonals / float(M.numStructs), 2);
    # bipartite-cores
    if M.numBiPartiteCores > 0 :
        model_cost += M.numBiPartiteCores * log(M.numBiPartiteCores / float(M.numStructs), 2);
    if M.numNearBiPartiteCores > 0 :
        model_cost += M.numNearBiPartiteCores * log(M.numNearBiPartiteCores / float(M.numStructs), 2);
    if M.numJellyFishes > 0 :
        model_cost += M.numJellyFishes * log(M.numJellyFishes / float(M.numStructs), 2);
    if M.numCorePeripheries > 0 :
        model_cost += M.numCorePeripheries * log(M.numCorePeripheries / float(M.numStructs), 2);

    # encode the structures
    if struc.isFullClique() :
        (cost,repeatedEdges,repeatedErrors) = LfullClique(struc,M,G,E);
        model_cost2 += cost;
    elif struc.isNearClique() :
        (cost,repeatedEdges,repeatedErrors) = LnearClique(struc,M,G,E);
        model_cost2 += cost;
    elif struc.isChain() :
        (cost,repeatedEdges,repeatedErrors) = Lchain(struc,M,G,E);
        model_cost2 += cost;
    elif struc.isStar() :
        (cost,repeatedEdges,repeatedErrors) = Lstar(struc,M,G,E);
        model_cost2 += cost;
    elif struc.isCorePeriphery() :
        (cost,repeatedEdges,repeatedErrors) = LcorePeriphery(struc,M,G,E);
        model_cost2 += cost;
    elif struc.isJellyFish() :
        (cost,repeatedEdges,repeatedErrors) = LjellyFish(struc,M,G,E);
        model_cost2 += cost;
    elif struc.isBiPartiteCore() :
        (cost,repeatedEdges,repeatedErrors) = LbiPartiteCore(struc,M,G,E);
        model_cost2 += cost;
    elif struc.isNearBiPartiteCore() :
        (cost,repeatedEdges,repeatedErrors) = LnearBiPartiteCore(struc,M,G,E);
        model_cost2 += cost;
    elif struc.isFullOffDiagonal() :
        (cost,repeatedEdges,repeatedErrors) = LfullOffDiagonal(struc,M,G,E);
        model_cost2 += cost;
    elif struc.isNearOffDiagonal() :
        (cost,repeatedEdges,repeatedErrors) = LnearOffDiagonal(struc,M,G,E);
        model_cost2 += cost;

    #print ">>>> repeated_errors = %.0f,\trepeated_edges = %.0f\tcovered = %.0f\tnewly_covered = %.0f" % (repeatedErrors,repeatedEdges,G.numEdges - E.numUnmodelledErrors, old_numUnmodelledErrors - E.numUnmodelledErrors); 
    #print ">?>? previously_covered = %.0f,\tnow_covered = %.0f" %(G.numEdges - old_numUnmodelledErrors, G.numEdges - E.numUnmodelledErrors);   

    # encode the error
    error_cost += 0 if E.numCellsCovered == 0 else log(E.numCellsCovered, 2);    # encode number of additive Errors
    if ((G.numNodes * G.numNodes - G.numNodes) / 2) - E.numCellsCovered > 0 :
        error_cost += log(((G.numNodes * G.numNodes - G.numNodes) / 2) - E.numCellsCovered, 2);    # encode number of Errors
 
    if errorEnc == "NP" :
        error_cost += LErrorNaivePrefix(G,M,E);
    elif errorEnc == "NB" :
        error_cost += LErrorNaiveBinom(G,M,E);
    elif errorEnc == "TP" :
        error_cost += LErrorTypedPrefix(G,M,E);
    elif errorEnc == "TB" :
        error_cost += LErrorTypedBinom(G,M,E);
    
    total_cost = model_cost + model_cost2 + error_cost;
    model_cost_total = model_cost + model_cost2;    
    # Minimize error and increase coverage
    total_cost_coverage = 1.0 * total_cost / (G.numEdges - E.numUnmodelledErrors + 1);
    # Minimize error and increase NEW coverage
    # Note: in this case the (NEW coverage) == coverage, since old coverage was 0
    total_cost_NEWcoverage = 1.0 * total_cost / (old_numUnmodelledErrors - E.numUnmodelledErrors + 1);
    total_cost_coverageRepeatedErr = 1.0 * total_cost * (repeatedEdges + 1) / (G.numEdges - E.numUnmodelledErrors + 1);
    total_cost_coverageRepeatedAll = 1.0 * total_cost * (repeatedErrors + repeatedEdges + 1) / (G.numEdges - E.numUnmodelledErrors + 1);

    #if old_numUnmodelledErrors - E.numUnmodelledErrors < 5 :
    #    toKeep = 'false';
    #elif 1.0 * ( repeatedErrors + 1) / (old_numUnmodelledErrors - E.numUnmodelledErrors + 1 ) > 1:
    #    toKeep = 'false';

    return (total_cost, model_cost_total, model_cost2, error_cost, E, total_cost_coverage, total_cost_NEWcoverage, total_cost_coverageRepeatedErr, total_cost_coverageRepeatedAll, toKeep);

    
    
    
    
