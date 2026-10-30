"""V21 local attack response.

This module deliberately separates recent combat response from the legion charge:
- hit pressure is a decaying, squad-local signal;
- healthy members keep a positive forward intent;
- wounded members receive bounded speed reduction, never reverse velocity;
- lateral avoidance choices use hysteresis/cooldowns and bounded displacement.
It is an overlay interface for motion_v17, not a replacement for the authoritative integrator.
"""
from collections import deque, defaultdict
from dataclasses import dataclass
import math
import numpy as np

@dataclass
class HitEvent:
    time: float
    member: int
    damage: int
    killed: bool

class LocalResponseV21:
    def __init__(self, units, config, window=0.75, hit_half_life=0.32):
        self.units = units
        self.config = config
        self.n = len(units)
        self.window = float(window)
        self.decay = math.log(2.0) / float(hit_half_life)
        self.squad_of = np.array([int(u.get('platoon', -1)) for u in units], dtype=int)
        keys = sorted(set(self.squad_of.tolist()))
        self.squad_ids = {k: i for i, k in enumerate(keys)}
        self.member_squad = np.array([self.squad_ids[k] for k in self.squad_of], dtype=int)
        self.squad_members = [np.where(self.member_squad == s)[0] for s in range(len(keys))]
        self.events = deque()
        self.hit_pressure = np.zeros(len(keys), dtype=float)
        self.proximity_pressure = np.zeros(len(keys), dtype=float)
        self.combat_pressure = np.zeros(len(keys), dtype=float)
        self.local_impulse = np.zeros(self.n, dtype=float)
        self.last_hit = np.full(self.n, -1e9, dtype=float)
        self.last_choice = np.zeros(self.n, dtype=float)
        self.avoid_side = np.zeros(self.n, dtype=np.int8)
        self.avoid_until = np.full(self.n, -1e9, dtype=float)
        self.cooldown_until = np.full(self.n, -1e9, dtype=float)
        self.stats = []

    def record_hit(self, member, damage, time, killed=False):
        member = int(member)
        if member < 0 or member >= self.n:
            raise IndexError(member)
        ev = HitEvent(float(time), member, int(max(1, damage)), bool(killed))
        self.events.append(ev)
        self.last_hit[member] = ev.time
        self.local_impulse[member] = min(1.0, self.local_impulse[member] + (0.60 if killed else 0.35))

    def _prune(self, time):
        cutoff = float(time) - self.window * 2.0
        while self.events and self.events[0].time < cutoff:
            self.events.popleft()

    def update(self, time, positions, hp=None, velocity=None, blue_positions=None, alive=None):
        time = float(time)
        p = np.asarray(positions, dtype=float)
        if p.shape != (self.n, 2):
            raise ValueError(f'positions must be ({self.n},2)')
        self._prune(time)
        if hp is None:
            hp = np.full(self.n, self.config.get('redHitPoints', 3), dtype=float)
        hp = np.asarray(hp)
        if alive is None:
            alive = hp > 0
        alive = np.asarray(alive, dtype=bool)
        for i in range(self.n):
            self.local_impulse[i] *= math.exp(-4.0 / 60.0)
        for s, members in enumerate(self.squad_members):
            active = members[alive[members]]
            denom = max(1, len(active))
            weighted = 0.0
            recent = 0
            killed = 0
            for e in self.events:
                if self.member_squad[e.member] != s:
                    continue
                age = time - e.time
                if age < 0 or age > self.window:
                    continue
                recent += 1
                killed += int(e.killed)
                weighted += math.exp(-self.decay * max(0.0, age)) * (1.0 + 0.5 * int(e.killed))
            self.hit_pressure[s] = min(1.0, weighted / denom)
            if blue_positions is not None and len(active):
                bp = np.asarray(blue_positions, dtype=float)
                front = active[np.argsort(p[active, 1])[-min(6, len(active)):]]
                d = np.linalg.norm(p[front, None, :] - bp[None, :, :], axis=2)
                distance = float(d.min())
                near = float(self.config.get('formationNearDistance', 18.0))
                far = float(self.config.get('formationFarDistance', 52.0))
                q = np.clip((distance - near) / max(1e-6, far - near), 0.0, 1.0)
                self.proximity_pressure[s] = 1.0 - q*q*(3.0 - 2.0*q)
            else:
                self.proximity_pressure[s] = 0.0
            self.combat_pressure[s] = float(np.clip(0.72 * self.proximity_pressure[s] + 0.28 * self.hit_pressure[s], 0.0, 1.0))
        # Output is member-level and never commands reverse motion.
        forward_intent = np.ones(self.n, dtype=float)
        speed_multiplier = np.ones(self.n, dtype=float)
        lateral_limit = np.full(self.n, 0.20, dtype=float)
        for i in range(self.n):
            s = self.member_squad[i]
            age = time - self.last_hit[i]
            if age >= 0:
                impulse = self.local_impulse[i]
                speed_multiplier[i] = max(0.55, 1.0 - 0.28 * impulse)
                lateral_limit[i] = min(0.34, 0.20 + 0.10 * impulse)
            # squad pressure only softens cohesion; it never reverses forward intent
            forward_intent[i] = 1.0 if alive[i] else 0.0
            if self.combat_pressure[s] > 0.7 and age >= 0:
                forward_intent[i] = max(0.88, forward_intent[i] - 0.04 * self.combat_pressure[s])
        result = dict(hitPressure=self.hit_pressure.copy(), proximityPressure=self.proximity_pressure.copy(), combatPressure=self.combat_pressure.copy(), forwardIntent=forward_intent, speedMultiplier=speed_multiplier, lateralLimit=lateral_limit)
        self.stats.append(dict(time=time, maxHitPressure=float(self.hit_pressure.max(initial=0.0)), maxCombatPressure=float(self.combat_pressure.max(initial=0.0)), healthyForwardP50=float(np.median(forward_intent[alive])) if np.any(alive) else 0.0))
        return result

    def choose_avoidance_side(self, member, time, left_clear, right_clear, obstacle=False):
        """Choose once, hold briefly, and respect cooldown. Returns -1/0/+1."""
        member = int(member); time = float(time)
        if time < self.avoid_until[member] and self.avoid_side[member] != 0:
            return int(self.avoid_side[member])
        if time < self.cooldown_until[member] and not obstacle:
            return int(self.avoid_side[member])
        left_clear, right_clear = float(left_clear), float(right_clear)
        if max(left_clear, right_clear) < 0.72:
            return 0
        if abs(left_clear - right_clear) < 0.08 and self.avoid_side[member] != 0:
            side = int(self.avoid_side[member])
        else:
            side = -1 if left_clear > right_clear else 1
        self.avoid_side[member] = side
        self.avoid_until[member] = time + 0.24
        self.cooldown_until[member] = time + 0.38
        return side

    def diagnostics(self):
        return dict(squads=len(self.squad_members), window=self.window, hitHalfLife=math.log(2.0)/self.decay, stats=self.stats)
