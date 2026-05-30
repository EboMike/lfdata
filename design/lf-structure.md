# LF structure

All the data managed by this system is based on the following concepts.

## Players

A player is an individual person. This system collects and aggregates the
stats of all games played by each player.

## Game

There are different types of LF games. Each type has some core data points
such as score or accuracy, but also typically many that are specific to the
game type.

The following game types are currently considered:

* SM5

## Team

### Colors

LF has a finite set of possible team colors, for example red, blue, green.

### Game teams

Each game type has a finite set of possible teams. For example, the SM5 game
type has a "fire" team using the red color, and an "earth" team using the
green color.

## Entity

An entity is an element in a game that be part of an event. Typical entities
are:

* Players
* Referees
* Bases

## Event

A game is typically described by a set of timestamped events. Each event
describes an action that involves one or two entities. An event can affect
other entities even if they are not explicitly mentioned in the event.

There is a finite set of possible actions per game type.
