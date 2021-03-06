
import scipy.stats
import sys
import os
import matplotlib
matplotlib.use("agg")
import ROOT
import argparse
from EventStore import EventStore
import numpy as np
import matplotlib.pyplot as plt




# command line arguments
parser = argparse.ArgumentParser()
parser.add_argument("filename", help="edm file to read", type=str)
parser.add_argument("--nevents", help="max number of events to process", type=int, default=5000)
parser.add_argument("--plotprefix", help="where to store the plots", type=str, default=os.environ.get("FCCPLOTS", ""))
parser.add_argument("--legacyCollectionNames", action="store_true",  help="create fake rate histograms", )
parser.add_argument("--overlayCollectionNames", action="store_true",  help="create fake rate histograms", )
args = parser.parse_args()

# easily switch between different branch naming conventions
collectionNames = {}
if args.legacyCollectionNames:
  collectionNames["GenParticles"] = "allGenParticles"
  collectionNames["SimParticles"] = "simParticles"
  collectionNames["TrackerPositionedHits"] = "positionedHits"
elif args.overlayCollectionNames:
  collectionNames["GenParticles"] = "mergedGenParticles"
  collectionNames["SimParticles"] = "mergedSimParticles"
  collectionNames["TrackerPositionedHits"] = "mergedTrackerPositionedHits"
else:
  collectionNames["GenParticles"] = "GenParticles"
  collectionNames["SimParticles"] = "SimParticles"
  collectionNames["TrackerPositionedHits"] = "TrackerPositionedHits"

events = EventStore([args.filename])
print len(events),  " events in rootfile ", args.filename

# lists to hold event data ntuples
l_etas = []
l_pts = []
l_dpts = []
l_true_pts = []
n_hitsPerTracks = []

# main event loop`
for i, store in enumerate(events):
    if i < args.nevents:
        print "event ", i
        trackStates = store.get('TrackStates')
        print "processing trackStates"
        print  "number of trackStates in event: ", len(trackStates)
        print "processing tracks ..."
        primaryTrackPresent = False
        tracks = store.get('Tracks')
        for t in tracks:
              print "\t track ID: ", t.bits()
              if t.bits() == 1:
                pos = []
                ids = []
                ts = t.states(0)
                trackparams = [
                  ts.d0(),
                  ts.z0(),
                  ts.phi(),
                  ts.theta(),
                  ts.qOverP() * -10,
                  ]

                pt = 1./trackparams[-1]
                if not np.isnan(pt):
                  l_pts.append(pt)
                  print "\ttrack parameters: ", trackparams
                  trackcov = [ts.cov()[0], ts.cov()[5], ts.cov()[9], ts.cov()[12], ts.cov()[14]] 
                  print "\ttrack covariances: ", trackcov
                  l_dpts.append(np.sqrt(trackcov[2]))
                  primaryTrackPresent = True
                  pos = []
                  #for j in range(t.hits_size()):
                  #  cor = t.hits(j).position()
                  #  pos.append([cor.x, cor.y, cor.z])
                  #pos = np.array(pos)
                  #n_hitsPerTracks.append(len(pos))
                  
                  
        print primaryTrackPresent
        if primaryTrackPresent:
          genparticles = store.get(collectionNames["GenParticles"])
          print "processing allGenParticles ..."
          for t in genparticles:
              momentum = [t.core().p4.px, t.core().p4.py, t.core().p4.pz, t.core().p4.mass]
              tm = ROOT.TLorentzVector(*momentum)
              print "\t sim Eta:", tm.Eta() 
              print "\t sim Pt:", tm.Pt() 
              print "\t rec Pt:", pt
              eta = tm.Eta()
              l_etas.append(tm.Eta())
              l_true_pts.append(np.rint(tm.Pt()))
              vertex = [0,0,0]
              print "\tsim trackID: ", t.core().bits, "sim pdgId: ", t.core().pdgId, "momentum: ", [t.core().p4.px, t.core().p4.py, t.core().p4.pz]
              print "\tsim phi: ", np.arctan(t.core().p4.py / t.core().p4.px)
              print "\tsim cottheta: ", t.core().p4.pz / np.sqrt(t.core().p4.px**2 +  t.core().p4.py**2)
              print "\tsim q_pT: ", 1. / np.sqrt(t.core().p4.px**2 +  t.core().p4.py**2)


etas = np.array(l_etas)
dpts = np.array(l_dpts)
pts = np.array(l_pts)
n_hitsPerTracks = np.array(n_hitsPerTracks)

print etas
print pts



colors = {
      1.: "black",
      2: "darkblue",
      5.: "blue",
      10.: "red",
      100.: "green",
      1000: "magenta",
      10000.: "darkgreen"
    }
root_graphs = {}
for e in np.unique(l_true_pts):
  print "pT: ", e
  i = np.array(l_true_pts) == e
  e = int(e)
  #plt.figure("n_hitsPerTracks")
  #plt.hist(n_hitsPerTracks[i], histtype="step", color=colors[e], range=(0,40), bins=40)
  plt.figure("pt_res")
  plt.semilogy(etas[i], np.abs(pts[i]), 'o', label=e, color=colors[e])
  plt.figure("dpt_res")
  plt.semilogy(etas[i], np.abs(dpts[i]), 'd', color=colors[e])
  plt.figure("pt_res_div")
  plt.semilogy(etas[i], np.abs(dpts[i]) / np.abs(pts[i]) * 100, 'o', alpha=0.4,  label=e, color=colors[e])

  plt.figure("pt_pull")
  pull = (np.abs(pts[i]) - np.abs(e)) * e  /  dpts[i] / 1000
  plt.hist(pull, color=colors[e], histtype="step")

  plt.figure("pt_res_div_binned")
  x = etas[i]
  y = np.abs(dpts[i]) / np.abs(pts[i]) * 100
  print "y", y
  print "x", x

  means_result = scipy.stats.binned_statistic(x, [y, y**2], bins=120, range=(0,5), statistic='mean')
  means, means2 = means_result.statistic
  standard_deviations = np.sqrt(means2 - means**2)
  bin_edges = means_result.bin_edges
  bin_centers = (bin_edges[:-1] + bin_edges[1:])/2.
  bin_width = (bin_edges[1] - bin_edges[0])

  clean = np.logical_not(np.isnan(means))
  means = means[clean]
  bin_centers = bin_centers[clean]

  plt.errorbar(x=bin_centers, y=means, xerr=bin_width, linestyle='-', marker='.', color=colors[e])
  print "means", means

  root_graphs[e] = ROOT.TGraph(len(bin_centers), bin_centers, means)
  root_graphs[e].SetName("Geant4 + RiemannFit, pT:  " + str(e) + " GeV ")
  root_graphs[e].SetTitle("Geant4 + RiemannFit, pT:  " + str(e) + " GeV; #eta; p_{t} / d p_{t}")


plt.figure("pt_res")
plt.xlabel(r"$\eta$")
plt.figure("dpt_res")
plt.xlabel(r"$\eta$")

plt.legend(loc="best", title="Pt [GeV]")
plt.figure("pt_res_div")
plt.xlabel(r"$\eta$", horizontalalignment='right', x=1.0)
plt.ylabel(r"$\frac {\delta p_T} {p_T} [\%] $", horizontalalignment='right', y=.95, rotation="horizontal", labelpad=-5)
plt.title(r"Track resolution for const Pt - no material effects")
plt.legend(loc="best", title="Pt [GeV]", framealpha=1.)

plt.figure("pt_pull")
plt.yscale('log', nonposy='clip')
plt.legend(loc="best", title="Pt [GeV]")
plt.xlabel(r"$\eta$")
plt.title("rpull of $p_t$")
plt.xlim(-2,2)

finalfig = plt.figure("pt_res_div_binned")
plt.gca().set_yscale("log", nonposy='clip')
plt.xlabel(r"$\eta$", horizontalalignment='right', x=1.0)
plt.ylabel(r"$\frac {\delta p_T} {p_T} [\%] $", horizontalalignment='right', y=.95, rotation="horizontal", labelpad=-5)
plt.title(r"Track resolution for const Pt across $\eta$")
plt.legend(loc="best", title="Pt [GeV]")

f = "SinglePartRes_" + args.filename.replace(".root", "") + "_nevents%05i" % args.nevents

figs = [plt.figure(n) for n in plt.get_fignums()]
for fig in [finalfig]: # use figs to save all plots
  plot_outfilename = os.path.join(args.plotprefix, f + "_" + fig._label + ".png")
  print "Writing plot ", plot_outfilename, "..."
  fig.savefig(plot_outfilename)

plt.show()


# write root graphs to file
rfile_out_name = os.path.join(args.plotprefix, "single_particle_resolution_graphs.root")
rfile_out = ROOT.TFile(rfile_out_name, "RECREATE")
rfile_out.cd()
for g in root_graphs.values():
  g.Write()
print "Wrote graphs to rootfile ", rfile_out_name, "..."

