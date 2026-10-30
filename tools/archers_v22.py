"""Per-member blue deployment/stance integrator; stable V18 control ABI.

Positions have one owner: ``move`` integrates velocity exactly once. Response
offsets are targets, never a second position writer. Distances/speeds are world
units, yaw is radians, gait phase is cycles.
"""
import math
import numpy as np
from scipy.spatial import cKDTree

NAMES = ['WAITING', 'MOVING', 'ARRIVING', 'AIMING', 'DRAWING',
         'RELEASING', 'RECOVERING', 'TURNING']
CONTROL_COLUMNS = ['state', 'timer', 'target', 'lastRelease', 'walkPhase',
                   'turnPhase', 'actionPhase', 'moveSpeed', 'facingYaw',
                   'targetYaw', 'stateProgress', 'releaseEventId']


def _angle(x):
    return (x + math.pi) % (2 * math.pi) - math.pi


def _limit(v, length):
    norm = float(np.linalg.norm(v))
    return v * (length / norm) if norm > length and norm > 1e-9 else v


class Archers:
    def __init__(self, units, C):
        self.units, self.C, self.n = units, C, len(units)
        self.starts = np.array([u['start'] for u in units], dtype=float)
        self.position = self.starts.copy()
        self.previous = self.starts.copy()
        self.velocity = np.zeros((self.n, 2))
        self.responseOffsets = np.zeros((self.n, 2))
        self.redPositions = None
        self.state = np.zeros(self.n, dtype=np.uint8)
        self.timer = np.zeros(self.n)
        self.target = np.full(self.n, -1, dtype=int)
        self.pendingStart = np.full(self.n, -1.)
        self.lastRelease = np.full(self.n, -10.)
        self.releaseEventId = np.full(self.n, -1, dtype=int)
        self.memberShots = np.zeros(self.n, dtype=int)
        self.groupShots = {u['group']: 0 for u in units}
        self.aimLeaseUntil = np.zeros(self.n)
        self.groupOpportunityTarget = {}
        self.openingShotMember = -1
        self.walkPhase = np.array([u.get('phase', 0.) % 1 for u in units])
        self.initialWalkPhase = self.walkPhase.copy()
        self.pathDistance = np.zeros(self.n)
        self.progress = np.zeros(self.n)
        self.moveSpeed = np.zeros(self.n)
        self.facingYaw = np.full(self.n, math.pi)
        self.targetYaw = self.facingYaw.copy()
        self.turnPhase = np.zeros(self.n)
        self.actionPhase = np.zeros(self.n)
        self.stateProgress = np.zeros(self.n)
        self.arrivedAt = np.full(self.n, np.nan)
        self.records, self.transitions = [], []
        self.personalSpace = float(C.get('blueMinimumSpacing', .615))
        self.spacing = float(C.get('blueSpacing', .94))
        self.defenseSlots = self.starts + [0., -C['blueAdvance']]
        self.slotOffsets = np.zeros((self.n, 2))
        self.shootingOffsets = np.zeros((self.n, 2))
        self.stanceWeight = np.zeros(self.n)
        for j, u in enumerate(units):
            q = ((j + 1) * .61803398875) % 1
            r = ((j + 1) * .41421356237 + u['group'] * .173) % 1
            row = (j % 36) // 6
            early = u['group'] in (0, 6)
            squad_lag = [0., .09, .17, .22, .15, .07, .04][u['group']]
            delay = .025 + squad_lag + .026 * row + .045 * r
            move_seconds = (1.08 if early else 1.62) + .055 * row + .06 * r
            speed = C.get('blueWalkSpeedReferenceDistance',C['blueAdvance']) / move_seconds * (.98 + .04 * q)
            u.update(delay=delay, moveSeconds=move_seconds,
                     walkSpeed=speed, walkAccel=speed * (4.1 + .5 * q),
                     walkBrake=speed * (5.1 + .5 * r),
                     turnSeconds=.12 + .10 * r,
                     maxTurnRate=4.3 + 1.1 * q,
                     aimSeconds=.07 + .08 * q + .018 * (u['group'] % 3),
                     drawSeconds=.17 + .07 * r,
                     recoverSeconds=.24 + .13 * q,
                     cycle=.57 + .12 * r,
                     arrival=delay + move_seconds + .27,
                     readyAt=delay + move_seconds + .44,
                     deploymentPathLength=float(C['blueAdvance']),
                     target=self.defenseSlots[j].tolist(),
                     shootYaw=math.pi, phaseOffset=q)
            # A stable personal target, not a changing random displacement.
            direction = np.array([math.cos(2 * math.pi * q),
                                  .72 * math.sin(2 * math.pi * q)])
            direction /= max(np.linalg.norm(direction), 1e-9)
            self.slotOffsets[j] = direction * self.spacing * (.075 + .025 * r)
            self.shootingOffsets[j] = direction * self.spacing * (.20 + .045 * r)
            u['slotOffset'] = self.slotOffsets[j].tolist()
            u['shootingOffset'] = self.shootingOffsets[j].tolist()
        self._lastTime = 0.

    def enter(self, j, state, t=None):
        if self.state[j] != state:
            self.transitions.append(dict(id=self.units[j]['id'],
                                         time=float(self._lastTime if t is None else t),
                                         state=NAMES[state]))
            self.state[j], self.timer[j] = state, 0.

    def _threat_yaw(self, j):
        if self.redPositions is not None and len(self.redPositions):
            d = np.asarray(self.redPositions) - self.position[j]
            target = int(self.target[j])
            v = d[target if 0 <= target < len(d) else
                  int(np.argmin(np.sum(d * d, axis=1)))]
            return math.atan2(v[0], v[1])
        return math.pi

    def _safe_velocity(self, desired, dt):
        """Project next-step pair constraints before the one position integral.

        Nearby pairs only. Corrections enter velocity; positions are not snapped.
        Already stationary/waiting neighbors are valid occupied obstacles.
        """
        v = desired.copy()
        search = self.personalSpace + 2 * max(1., np.max(np.linalg.norm(v, axis=1))) * dt
        pairs = sorted(cKDTree(self.position).query_pairs(search))
        for _ in range(4):
            for a, b in pairs:
                rel = self.position[b] - self.position[a]
                predicted = rel + (v[b] - v[a]) * dt
                distance = float(np.linalg.norm(predicted))
                if distance >= self.personalSpace:
                    continue
                norm = predicted / max(distance, 1e-9)
                if distance < 1e-8:
                    norm = rel / max(np.linalg.norm(rel), 1e-9)
                needed = (self.personalSpace - distance) / dt
                mobile_a = self.state[a] != 0
                mobile_b = self.state[b] != 0
                count = int(mobile_a) + int(mobile_b)
                if count:
                    if mobile_a: v[a] -= norm * needed / count
                    if mobile_b: v[b] += norm * needed / count
        return v

    def move(self, t, dt):
        self._lastTime = float(t)
        self.previous[:] = self.position
        desired = np.zeros_like(self.velocity)
        for j, u in enumerate(self.units):
            if getattr(self,'deadMask',None) is not None and self.deadMask[j]:
                self.state[j]=0
                continue
            if t < u['delay']:
                continue
            if self.state[j] == 0:
                self.enter(j, 1)
            self.timer[j] += dt if self.state[j] in (1, 2, 7) else 0.
            attack = self.state[j] in (3, 4, 5, 6)
            wanted_weight = 1. if attack else 0.
            self.stanceWeight[j] += np.clip(wanted_weight - self.stanceWeight[j],
                                           -dt * 3., dt * 3.)
            offset = (self.slotOffsets[j] * (1 - self.stanceWeight[j]) +
                      self.shootingOffsets[j] * self.stanceWeight[j])
            # Both personal offsets and externally computed response targets
            # pass through the same damped, acceleration-limited integrator.
            response = _limit(np.asarray(self.responseOffsets[j]), self.spacing * .38)
            goal = self.defenseSlots[j] + offset + response
            error = goal - self.position[j]
            distance = float(np.linalg.norm(error))
            independent_deployment = self.C.get('parallelAssemblyFire', False)
            locomoting = distance >= .045 or np.linalg.norm(self.velocity[j]) >= .42
            if self.state[j] in (1, 2) or independent_deployment and locomoting:
                desired_speed = min(u['walkSpeed'], math.sqrt(2 * u['walkBrake'] * distance))
                # Critically damped approach prevents endpoint snap/oscillation.
                desired_speed = min(desired_speed, distance * 10.)
                desired_velocity = error / max(distance, 1e-9) * desired_speed
                if distance < u['walkSpeed'] ** 2 / (2 * u['walkBrake']) + .12:
                    if self.state[j] in (1, 2):self.enter(j, 2)
                if distance < .045 and np.linalg.norm(self.velocity[j]) < .42:
                    self.arrivedAt[j] = t
                    u['arrival'] = float(t)
                    if self.state[j] in (1, 2):self.enter(j, 7)
            else:
                # Bounded spring + damping. This is a velocity target, not
                # direct slot placement or a post-render additive displacement.
                desired_velocity = _limit(error * 8., .85)
            if getattr(self,'evasionVelocity',None) is not None and self.melee_blocked(j):
                desired_velocity=self.evasionVelocity[j]
            acceleration = _limit((desired_velocity - self.velocity[j]) * 14.,
                                  u['walkAccel'] if np.dot(desired_velocity, self.velocity[j]) >= 0
                                  else u['walkBrake'])
            desired[j] = self.velocity[j] + acceleration * dt
            self.targetYaw[j] = self._threat_yaw(j)
            if independent_deployment and not self.melee_blocked(j) and self.state[j] in (1,2) and t >= u['delay'] + .10 + .12*u['phaseOffset']:
                # Preparation may overlap assembly, but target selection and
                # release still use real range, individual aim/draw and facing.
                self.enter(j,3,t)
            if self.state[j] in (1, 2) and np.linalg.norm(desired[j]) > .2:
                yaw = math.atan2(desired[j, 0], desired[j, 1])
            else:
                yaw = self.targetYaw[j]
            delta = _angle(yaw - self.facingYaw[j])
            self.facingYaw[j] += np.clip(delta, -u['maxTurnRate'] * dt,
                                        u['maxTurnRate'] * dt)
            if self.state[j] == 7:
                self.turnPhase[j] = min(1., self.timer[j] / u['turnSeconds'])
                if self.turnPhase[j] >= 1 and abs(delta) < .10:
                    u['readyAt'] = float(t)
                    self.enter(j, 3)
        projector=getattr(self,'jointVelocityProjector',None)
        self.velocity[:] = projector(desired,dt) if projector else self._safe_velocity(desired, dt)
        self.position += self.velocity * dt
        actual_step = np.linalg.norm(self.position - self.previous, axis=1)
        self.pathDistance += actual_step
        self.walkPhase = (self.walkPhase + actual_step / max(self.C['blueStride'], 1e-6)) % 1
        self.moveSpeed[:] = actual_step / dt
        self.progress[:] = np.clip((self.starts[:, 1] - self.position[:, 1]) /
                                   max(self.C['blueAdvance'], 1e-6), 0, 1)
        self._phases()

    def _phases(self):
        for j, u in enumerate(self.units):
            st, elapsed = int(self.state[j]), self.timer[j]
            if st in (0, 1, 2):
                self.actionPhase[j] = self.walkPhase[j]
                self.stateProgress[j] = self.progress[j]
            elif st == 7:
                self.actionPhase[j] = 0.
                self.stateProgress[j] = self.turnPhase[j]
            elif st == 3:
                progress = min(1., elapsed / u['aimSeconds'])
                self.stateProgress[j] = progress
                self.actionPhase[j] = .12 * progress
            elif st == 4:
                progress = min(1., elapsed / u['drawSeconds'])
                self.stateProgress[j] = progress
                self.actionPhase[j] = .12 + .52 * progress
            elif st == 5:
                self.stateProgress[j], self.actionPhase[j] = 1., .64
            elif st == 6:
                progress = min(1., elapsed / u['recoverSeconds'])
                self.stateProgress[j] = progress
                self.actionPhase[j] = .64 + .36 * progress

    def select(self, j, red, hp, reserved, t):
        distance = np.linalg.norm(red - self.position[j], axis=1)
        valid = np.where((hp > 0) & (~reserved) & (distance <= self.C['archerRange']))[0]
        if not len(valid): return -1
        pool = valid[np.argsort(distance[valid], kind='stable')[:8]]
        return int(pool[j % len(pool)])

    def _opportunity_targets(self, red, hp, reserved):
        """One future firing opportunity per unrepresented interior squad.

        A planning hold is not a target lock or an out-of-range shot: only
        AIMING allocation is affected. No DRAWING/in-flight commitment moves.
        Keeping a handful of front targets available prevents early wings
        reserving every target until after the deeper squads' safe cut.
        """
        groups = sorted(self.groupShots)
        centers = {g: self.defenseSlots[[j for j,u in enumerate(self.units)
                                        if u['group']==g]].mean(axis=0) for g in groups}
        shallow = min(v[1] for v in centers.values())
        drawn = {int(self.target[j]) for j in np.flatnonzero(self.state==4)
                 if self.target[j]>=0}
        opening = int(self.target[self.openingShotMember]) if self.openingShotMember>=0 else -1
        eligible = [g for g in groups if centers[g][1]>shallow+2.
                    and self.groupShots[g]==0]
        for g in list(self.groupOpportunityTarget):
            target=self.groupOpportunityTarget[g]
            if g not in eligible or hp[target]<=0 or (reserved[target] and target not in drawn) or target==opening:
                self.groupOpportunityTarget.pop(g)
        used=set(self.groupOpportunityTarget.values())|drawn
        if opening>=0:used.add(opening)
        for g in sorted(eligible,key=lambda g:-centers[g][1]):
            if g in self.groupOpportunityTarget:continue
            if any(self.units[j]['group']==g and self.state[j]==4 for j in range(self.n)):continue
            valid=np.flatnonzero((hp>0)&(~reserved))
            valid=np.array([k for k in valid if k not in used],dtype=int)
            if len(valid):
                distance=np.linalg.norm(red[valid]-centers[g],axis=1)
                target=int(valid[np.argmin(distance)])
                self.groupOpportunityTarget[g]=target;used.add(target)
        return self.groupOpportunityTarget

    def _allocate_aiming(self, t, red, hp, reserved):
        """Fair noncommitted leases; drawn bows and in-flight arrows are locks.

        Each allocation increases its squad's load, so newly eligible squads
        can acquire targets before already represented wings reacquire them.
        Existing short AIMING leases win ties inside their squad. Neither
        launch timing nor a committed target is moved by this allocator.
        """
        opportunities = self._opportunity_targets(red,hp,reserved)
        claimed = {int(v): j for j, v in enumerate(self.target)
                   if v >= 0 and self.state[j] == 4}
        load = dict(self.groupShots)
        for j in np.flatnonzero(self.state == 4):
            load[self.units[j]['group']] += 1
        candidates = list(np.flatnonzero(self.state == 3))
        old_targets = self.target.copy()
        for j in candidates:
            self.target[j] = -1
        while candidates:
            def priority(j):
                u = self.units[j]
                lease = old_targets[j] >= 0 and t < self.aimLeaseUntil[j]
                return (load[u['group']], self.memberShots[j], not lease,
                        -min(1., self.timer[j] / u['aimSeconds']),
                        self.lastRelease[j], j)
            j = min(candidates, key=priority)
            candidates.remove(j)
            excluded = self.reserved_for_member(j, reserved).copy()
            for target in claimed:
                excluded[target] = True
            # The opening opportunity is exempt: no squad coordination may
            # postpone the earliest ready wing's first physically valid arrow.
            opening_exempt = self.openingShotMember < 0 or j == self.openingShotMember and not self.records
            if not opening_exempt:
                for g,target in opportunities.items():
                    if g != self.units[j]['group']: excluded[target]=True
            old = int(old_targets[j])
            valid_old = (old >= 0 and hp[old] > 0 and not excluded[old]
                         and np.linalg.norm(red[old] - self.position[j]) <= self.C['archerRange'])
            target = old if valid_old else self.select(j, red, hp, excluded, t)
            self.target[j] = target
            if target >= 0:
                if self.openingShotMember < 0:self.openingShotMember=int(j)
                claimed[target] = j
                load[self.units[j]['group']] += 1
                if target != old:
                    self.aimLeaseUntil[j] = t + self.units[j]['aimSeconds'] + .05
            if target != old and not self.C.get('preAim', False):
                self.timer[j] = 0.

    def reserved_for_member(self, j, reserved):
        return reserved

    def melee_blocked(self,j):
        return getattr(self,'meleeBlocked',None) is not None and bool(self.meleeBlocked[j])

    def ready_to_draw(self, j, t):
        return True

    def on_release(self, j, target, event):
        pass

    def update_fire(self, t, dt, red, hp, reserved, spawn):
        self.redPositions = red
        self._allocate_aiming(t, red, hp, reserved)
        claimed = {int(v): j for j, v in enumerate(self.target)
                   if v >= 0 and self.state[j] in (3, 4)}
        for j, u in enumerate(self.units):
            st = int(self.state[j])
            if self.melee_blocked(j) or (getattr(self,'deadMask',None) is not None and self.deadMask[j]):continue
            if st not in (3, 4, 5, 6): continue
            member_reserved = self.reserved_for_member(j, reserved)
            target = int(self.target[j])
            valid = (target >= 0 and hp[target] > 0 and not member_reserved[target]
                     and claimed.get(target, j) == j
                     and np.linalg.norm(red[target] - self.position[j]) <= self.C['archerRange'])
            if st == 3:
                if not valid:
                    if claimed.get(target) == j: claimed.pop(target)
                    excluded = member_reserved.copy()
                    for other, owner in claimed.items():
                        if owner != j: excluded[other] = True
                    if j != self.openingShotMember or self.records:
                        for g,held in self.groupOpportunityTarget.items():
                            if g != u['group']: excluded[held]=True
                    target = self.select(j, red, hp, excluded, t)
                    self.target[j] = target
                    if target >= 0: claimed[target] = j
                    # Only test C may raise the bow while waiting for range.
                    if not self.C.get('preAim', False): self.timer[j] = 0.
                if target >= 0 or self.C.get('preAim', False): self.timer[j] += dt
                if (target >= 0 and self.timer[j] >= u['aimSeconds']
                        and self.ready_to_draw(j, t)
                        and abs(_angle(self.targetYaw[j] - self.facingYaw[j])) < .16):
                    self.pendingStart[j] = t
                    self.enter(j, 4, t)
            elif st == 4:
                if not valid:
                    self.target[j] = -1
                    self.enter(j, 3, t)
                else:
                    self.timer[j] += dt
                    if self.timer[j] >= u['drawSeconds']:
                        event = spawn(j, target, t, self.pendingStart[j])
                        reserved[target] = True
                        self.on_release(j, target, event)
                        self.records.append(event)
                        self.memberShots[j] += 1
                        self.groupShots[u['group']] += 1
                        self.releaseEventId[j] = int(str(event.get('id', len(self.records)-1)).lstrip('A'))
                        self.lastRelease[j] = t
                        self.enter(j, 5, t)
            elif st == 5:
                self.enter(j, 6, t)
            else:
                self.timer[j] += dt
                if self.timer[j] >= u['recoverSeconds']:
                    self.target[j] = -1
                    self.enter(j, 3, t)
            if target >= 0:
                d = red[target] - self.position[j]
                self.targetYaw[j] = math.atan2(d[0], d[1])
        self._phases()

    def control(self):
        return np.column_stack([self.state, self.timer, self.target,
                                self.lastRelease, self.walkPhase, self.turnPhase,
                                self.actionPhase, self.moveSpeed, self.facingYaw,
                                self.targetYaw, self.stateProgress, self.releaseEventId])

    def record_combat(self, *args, **kwargs):
        """Compatibility hook; response controller owns event interpretation."""
        return None
