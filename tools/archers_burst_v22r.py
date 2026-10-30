"""Bounded first-shot reservations. Original draw/recovery/flight/damage remain."""
import collections
import numpy as np
from archers_v22 import Archers as OriginalArchers

class Archers(OriginalArchers):
    def __init__(self,units,config):
        super().__init__(units,config)
        self.firstOpportunity=np.full(self.n,np.nan)
        self.redUnits=[]
        self.pendingCount=None;self.pendingDamage=None;self.currentHP=None
        self.openingMask=None
        self.coverage=collections.Counter()

    def set_pending(self,count,damage,hp):
        self.pendingCount=count.copy();self.pendingDamage=damage.copy();self.currentHP=hp.copy()
        self.openingMask=(hp<=0)|(count>=self.C['openingPendingArrowCap'])|(damage>=hp)

    def reserved_for_member(self,j,reserved):
        if self.memberShots[j]>0 or self.openingMask is None:return reserved
        planned=3 if j%17==0 else 1
        return self.openingMask | (self.currentHP-self.pendingDamage<planned)

    def _opportunity_targets(self,red,hp,reserved):
        # No out-of-range squad holds during this independent opening test.
        return {}

    def select(self,j,red,hp,reserved,t):
        if self.memberShots[j]>0:return super().select(j,red,hp,reserved,t)
        distance=np.linalg.norm(red-self.position[j],axis=1)
        valid=np.flatnonzero((hp>0)&(~reserved)&(distance<=self.C['archerRange']))
        if not len(valid):return -1
        pool=valid[np.argsort(distance[valid],kind='stable')[:48]]
        # Cover exposed members in several platoons; C2 can finish already
        # damaged targets with actual subsequent arrows, never fake damage.
        score=distance[pool].copy()
        for k,target in enumerate(pool):
            platoon=self.redUnits[int(target)]['platoon']
            score[k]+=.28*self.coverage[platoon]
            score[k]-=self.C['openingFinishWoundedWeight']*(self.C['redHitPoints']-hp[target])
        return int(pool[np.argmin(score)])

    def ready_to_draw(self,j,t):
        if self.memberShots[j]>0:return True
        if not np.isfinite(self.firstOpportunity[j]):self.firstOpportunity[j]=t
        return t-self.firstOpportunity[j]>=self.C['openingDrawStagger']*self.units[j]['phaseOffset']-1e-9

    def on_release(self,j,target,event):
        # Prevent another first-shot commitment to this target in this frame;
        # the next frame recomputes the actual outstanding damage budget.
        self.openingMask[target]=True
        if self.memberShots[j]==0:self.coverage[self.redUnits[int(target)]['platoon']]+=1
