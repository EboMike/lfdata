"""Main command line interface for the LF data tool."""

import argparse
import sys

from lfdata.importer import TdfImporter
from lfdata.replay import LFReplaySystem


def main() -> None:
    """Parses command line arguments and runs the LF data tool."""
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(
        description='Manage LF data: import from TDF and print replays.'
    )
    parser.add_argument(
        '--input_tdf',
        type=str,
        help='Filename of a TDF file. The data of this file will be read.',
    )
    parser.add_argument(
        '--print_replay',
        action='store_true',
        help='Prints all replay events to the output.',
    )
    parser.add_argument(
        '--state_at',
        type=int,
        help=(
            'Prints the complete game state given at the specific '
            'number of milliseconds into the game.'
        ),
    )
    parser.add_argument(
        '--video_player',
        type=str,
        help='The name of the player to focus the video generation on.',
    )
    parser.add_argument(
        '--video_state_at',
        type=int,
        help=(
            'All UI elements given at the specific number of '
            'milliseconds into the game.'
        ),
    )
    parser.add_argument(
        '--image-outdir',
        type=str,
        default='.',
        help=(
            'Folder to place all output images in. '
            'Defaults to the current directory.'
        ),
    )
    parser.add_argument(
        '--image-at',
        type=int,
        help=(
            'Renders an image to be used at the specific number of '
            'milliseconds into the game. The image will be saved as '
            'a PNG file.'
        ),
    )
    parser.add_argument(
        '--video_start_ms',
        type=int,
        default=0,
        help=(
            'Milliseconds into the game into which to start '
            'generating video frames for. Defaults to 0.'
        ),
    )
    parser.add_argument(
        '--video_end_ms',
        type=int,
        help=(
            'Milliseconds into the game until which to generate '
            'video frames for. If not specified, will generate '
            'frames until 10 seconds after the game is over.'
        ),
    )
    parser.add_argument(
        '--video_out',
        type=str,
        help=(
            'Filename of the video to generate from the images '
            'that were rendered.'
        ),
    )

    args = parser.parse_args()

    if not args.input_tdf:
        parser.print_help()
        sys.exit(1)

    importer = TdfImporter(args.input_tdf)
    game = importer.parse()

    if args.print_replay:
        replay = LFReplaySystem(game)
        records = replay.run()
        for record in records:
            print(f'{record.time_ms:07d}\t{record.description}')

    if args.state_at is not None:
        replay = LFReplaySystem(game)
        replay.run_up_to(args.state_at)

        sorted_teams = sorted(
            replay.game_state.teams.values(), key=lambda t: t.ranking
        )
        print(f'Game State at {args.state_at} ms:')
        print('\nTeams:')
        for team in sorted_teams:
            print(f'  Rank {team.ranking}: {team.name} - Score: {team.score}')

        print('\nPlayers:')
        sorted_players = sorted(
            replay.game_state.players.values(),
            key=lambda p: p.score,
            reverse=True,
        )
        for p in sorted_players:
            codename = replay.entity_names.get(p.entity_id, p.entity_id)
            if p.is_eliminated():
                state_str = 'Eliminated'
            elif p.is_down(args.state_at):
                state_str = f'Down (until {p.downtime_ends_at_ms} ms)'
            else:
                state_str = 'Active'
            print(
                f'  {codename} ({p.role.display_name}): '
                f'Score={p.score}, Lives={p.lives}, Shots={p.shots}, '
                f'Missiles={p.missiles}, Special Points={p.special_points}, '
                f'State={state_str}'
            )

    if args.video_state_at is not None:
        from lfdata.video import VisualElementGenerator

        hud_gen = VisualElementGenerator(game, args.video_player)
        elements = hud_gen.generate_at(args.video_state_at)

        if args.video_player:
            print(
                f'HUD Elements for player {args.video_player} '
                f'at {args.video_state_at} ms:'
            )
        else:
            print(f'HUD Elements at {args.video_state_at} ms:')

        for el in elements:
            if el.element_type == 'text':
                coord_str = (
                    f'  [x={el.x}, y={el.y}, '
                    f'align={el.align}, alpha={el.alpha:.2f}]'
                )
                style_str = (
                    f'(font={el.style.font}, style={el.style.style}, '
                    f'size={el.style.size}, color={el.style.color}, '
                    f'bg_color={el.style.background_color})'
                )
                print(f'{coord_str} Text: {el.text} {style_str}')
            elif el.element_type == 'downtime_bar':
                coord_str = (
                    f'  [x={el.x}, y={el.y}, '
                    f'extents={el.extents}, alpha={el.alpha:.2f}]'
                )
                print(
                    f'{coord_str} Downtime Bar: safe_ms={el.safe_ms}, '
                    f'resettable_ms={el.resettable_ms}'
                )
            elif el.element_type == 'scoreboard':
                coord_str = (
                    f'  [x={el.x}, y={el.y}, '
                    f'align={el.align}, alpha={el.alpha:.2f}]'
                )
                style_str = (
                    f'(font={el.style.font}, style={el.style.style}, '
                    f'size={el.style.size})'
                )
                print(f'{coord_str} Scoreboard {style_str}:')
                for team in el.scoreboard_data['teams']:
                    team_name = team['team_name']
                    rank = team['visual_rank']
                    score = team['team_score']
                    print(
                        f'    {team_name} '
                        f'(visual_rank={rank:.2f}) - Score: {score}'
                    )
                    header = (
                        f'      {"Player":<20} | '
                        f'{"Role":<12} | '
                        f'{"Score":>6} | '
                        f'{"Lives":>5} | '
                        f'{"Shots":>5} | '
                        f'{"Missiles":>8} | '
                        f'{"Spec":>5}'
                    )
                    print(header)
                    print(f'      {"-" * 79}')
                    for p in team['players']:
                        if p['is_eliminated']:
                            state_suffix = ' (Eliminated)'
                        elif p['is_down']:
                            state_suffix = ' (Down)'
                        else:
                            state_suffix = ''

                        codename_display = p['codename'] + state_suffix

                        row = (
                            f'      {codename_display:<20} | '
                            f'{p["role_name"]:<12} | '
                            f'{p["score"]:>6} | '
                            f'{p["lives"]:>5} | '
                            f'{p["shots"]:>5} | '
                            f'{p["missiles"]:>8} | '
                            f'{p["special_points"]:>5}'
                        )
                        print(row)
                    print(f'      {"-" * 79}')
                    tot = team['totals']
                    total_row = (
                        f'      {"TOTAL":<20} | '
                        f'{"":<12} | '
                        f'{tot["score"]:>6} | '
                        f'{tot["lives"]:>5} | '
                        f'{tot["shots"]:>5} | '
                        f'{tot["missiles"]:>8} | '
                        f'{tot["special_points"]:>5}'
                    )
                    print(total_row)

    if args.image_at is not None:
        from pathlib import Path
        from lfdata.video import VideoGenerator, VisualElementGenerator

        generator = VideoGenerator(game)
        config = generator._load_config(None)
        if args.video_player:
            config['player_name'] = args.video_player

        hud_gen = VisualElementGenerator(game, args.video_player, config)
        elements = hud_gen.generate_at(args.image_at)
        img = generator._render_frame(elements, args.image_at, config)

        out_dir = Path(args.image_outdir)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f'image_at_{args.image_at}.png'
        img.save(out_path)
    elif (
        args.video_player is not None or args.video_out is not None
    ) and args.video_state_at is None:
        from pathlib import Path
        from lfdata.video import VideoGenerator, VisualElementGenerator

        generator = VideoGenerator(game)
        config = generator._load_config(None)
        if args.video_player is not None:
            config['player_name'] = args.video_player

        hud_gen = VisualElementGenerator(game, args.video_player, config)

        actual_duration_ms = game.duration
        if hud_gen.game_ended_at_ms is not None:
            actual_duration_ms = hud_gen.game_ended_at_ms
        if actual_duration_ms is None:
            actual_duration_ms = 0

        if args.video_end_ms is not None:
            end_ms = args.video_end_ms
        else:
            if not game.events:
                end_ms = 0
            else:
                extra_footage_ms = config.get('extra_footage_ms', 10000)
                end_ms = actual_duration_ms + extra_footage_ms

        start_ms = args.video_start_ms
        fps = config.get('fps', 60)

        out_dir = Path(args.image_outdir)
        out_dir.mkdir(parents=True, exist_ok=True)

        if args.video_out:
            generator.generate(
                output_path=args.video_out,
                config_path=None,
                video_start_ms=start_ms,
                video_end_ms=args.video_end_ms,
                video_player=args.video_player,
            )
        else:
            generator._generate_frames(
                temp_path=out_dir,
                start_ms=start_ms,
                end_ms=end_ms,
                fps=fps,
                config=config,
                hud_gen=hud_gen,
            )


if __name__ == '__main__':
    main()
