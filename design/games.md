# General game type

Each game type will be described in dedicated design files, but there are rules
that apply to most game types:

## Player entities

In almost all game types, a player will zap other players. There will be events
for zapping a player and possibly events for missing a player. In some game
types, a player can have a role. For example, in SM5, a player could be a Scout
or a Commander or Heavy or Ammo or Medic. In some game types, a player has a
limited amount of lives. In some game types, a player has a limited amount of
ammo. In most games, a player has a score.

## Special points

In some game types, a player can have "special points". This is a separate data
point that increases as the player performs certain actions. These points can be
used to perform actions.

## Player downtime

If a player is zapped, they are "down". For a specific amount of time, they will
not be able to zap. There are two phases of downtime: "Safe" - the player cannot
zap and cannot be zapped. "Resettable" - the player cannot zap, but can be zapped
by others. The duration of each depends on the game type.

## Base entities

Bases are typically physical devices in the arena that can be zapped by a player.

## Referees

A referee can penalize a player, which could result in downtime, or loss of points,
or something else.

## Games

A game will run for a specific amount of time. In some game types, the game can end
prematurely if specific conditions are met.

In most game types, the team with the highest combined score wins.

## Missiles

Some game types have missiles. A player can lock a target with a missile, and then
fire the missile.

