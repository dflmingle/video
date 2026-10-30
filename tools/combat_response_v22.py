"""Local, causal BLUE response intent; never integrates an archer root.

Coordinates are X/Z. Real arrow impacts encourage a small step toward the
specific target. Synthetic damage is an explicitly flagged diagnostic only.
The caller's collision/spring integrator remains the sole position owner.
"""
import math
import numpy as np


class CombatResponseV22:
    MAX_OFFSET = .235

    def __init__(self, blue_units, starts=None, config=None):
        self.units = blue_units
        self.nblue = len(blue_units)
        self.config = config or {}
        self.starts = np.asarray(starts if starts is not None else
                                 [u['start'] for u in blue_units], dtype=float)
        self.groups = np.asarray([u.get('group', 0) for u in blue_units])
        self.events = []
        self.audit = []
        self.offset = np.zeros((self.nblue, 2))
        self.cooldown = np.full(self.nblue, -1e9)
        self.last_time = -1e9
        self.diagnostic_event_count = 0

    def record_impact(self, shooter, target, damage, killed, t):
        """Call exactly once after an existing bound arrow impact is resolved.

        target is a RED-local index into offsets(..., redPositions).
        """
        shooter, target = int(shooter), int(target)
        if not 0 <= shooter < self.nblue:
            raise IndexError(shooter)
        if target < 0 or damage <= 0:
            raise ValueError('Impact requires a red target and positive damage')
        event = dict(time=float(t), shooter=shooter, target=target,
                     damage=float(damage), killed=bool(killed), diagnostic=False,
                     participants=None, direction=None)
        self.events.append(event)
        self.audit.append({k: v for k, v in event.items()
                           if k not in ('participants', 'direction')})

    def record_damage(self, archer, damage, t, *, diagnostic=False):
        """Test-only retreat signal. Never invent production blue damage."""
        if not diagnostic:
            raise ValueError('No blue damage source: diagnostic=True is required')
        archer = int(archer)
        if not 0 <= archer < self.nblue or damage <= 0:
            raise ValueError('Invalid diagnostic blue damage')
        self.events.append(dict(time=float(t), shooter=archer, target=None,
                                damage=float(damage), killed=False,
                                diagnostic=True, participants=None, direction=None))
        self.diagnostic_event_count += 1
        self.audit.append(dict(time=float(t), archer=archer, damage=float(damage),
                               diagnostic=True, source='DIAGNOSTIC_BLUE_DAMAGE'))

    def _activate(self, event, positions, red_positions):
        j = event['shooter']
        direction = np.array([0., -1.])
        if not event['diagnostic'] and red_positions is not None:
            if event['target'] >= len(red_positions):
                raise IndexError('record_impact target must be RED-local')
            direction = red_positions[event['target']] - positions[j]
            direction /= max(1e-9, float(np.linalg.norm(direction)))
        if event['diagnostic']:
            direction *= -1
        event['direction'] = direction
        # Only the firing member + at most two nearby FRONT friends react.
        # No event can shift the full U or a whole squad.
        peers = np.where(self.groups == self.groups[j])[0]
        forward = (positions[peers] - positions[j]) @ direction
        front_threshold = float(np.max(forward)) - 1.1
        front = peers[forward >= front_threshold]
        distances = np.linalg.norm(positions[front] - positions[j], axis=1)
        candidates = front[np.argsort(distances, kind='stable')]
        selected = [j] if event['time'] >= self.cooldown[j] else []
        for k in candidates:
            k = int(k)
            if k == j or len(selected) >= 3:
                continue
            if np.linalg.norm(positions[k] - positions[j]) <= 1.75 and event['time'] >= self.cooldown[k]:
                selected.append(k)
        event['participants'] = selected
        for k in selected:
            self.cooldown[k] = event['time'] + .42

    def offsets(self, t, positions, dt, redPositions=None):
        """Returns bounded desired offsets, NOT displacements to apply each tick.

        A .12s attack, .20s hold, .40s exponential tail gives visible persistence
        without event accumulation. Repeated hits normalize by max, not sum.
        """
        t, dt = float(t), float(dt)
        p = np.asarray(positions, dtype=float)
        red = None if redPositions is None else np.asarray(redPositions, dtype=float)
        if p.shape != (self.nblue, 2) or dt <= 0 or t < self.last_time - 1e-9:
            raise ValueError('Expected forward fixed-time updates and nblue x 2 positions')
        self.last_time = t
        desired = np.zeros_like(self.offset)
        weights = np.zeros(self.nblue)
        active = []
        for e in self.events:
            age = t - e['time']
            if age < 0:
                active.append(e)
                continue
            if age > 1.8:
                continue
            active.append(e)
            if e['participants'] is None:
                self._activate(e, p, red)
            attack = min(1., age / .12)
            decay = math.exp(-max(0., age - .32) / .40)
            amplitude = (.18 if e['diagnostic'] else .205 if e['killed'] else .135)
            for order, j in enumerate(e['participants']):
                strength = amplitude * attack * decay * (1. if order == 0 else .55)
                if strength > weights[j]:
                    desired[j] = e['direction'] * strength
                    weights[j] = strength
        self.events = active
        # Intent itself is continuous; caller applies its own physical spring.
        alpha = 1 - math.exp(-dt / .075)
        self.offset += (desired - self.offset) * alpha
        length = np.linalg.norm(self.offset, axis=1)
        self.offset *= np.minimum(1., self.MAX_OFFSET / np.maximum(1e-12, length))[:, None]
        return self.offset.copy()

    update = offsets


CombatResponse = CombatResponseV22
Response = CombatResponseV22
