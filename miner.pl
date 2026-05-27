#!/usr/bin/env perl
use strict;
use warnings;
use IPC::Open2;
use Symbol qw(gensym);

my $deep     = 0;
my $clean    = 1;
my $all      = 0;
my @corpora;

while (@ARGV) {
    my $arg = shift @ARGV;

    if ($arg eq '-d' || $arg eq '--deep') {
        $deep = 1;
    }
    elsif ($arg eq '--no-clean') {
        $clean = 0;
    }
    elsif ($arg eq '-a' || $arg eq '--all') {
        $all = 1;
    }
    elsif ($arg eq '-h' || $arg eq '--help') {
        usage();
        exit 0;
    }
    elsif ($arg =~ /^-/) {
        die "Unknown option: $arg\n";
    }
    else {
        push @corpora, $arg;
    }
}

if (!@corpora) {
    @corpora = ("$ENV{HOME}/Chinese Text Analysis/");

    if ($deep) {
        push @corpora,
            "$ENV{HOME}/src/TurnBasedGameData/",
            "$ENV{HOME}/src/AnimeGameData/";
    }
}

my @rg_base = (
    'rg',
    '--no-filename',
    '-N',
    '-uu',
    @corpora,
    '-g', '!old/',
    '-g', '!Anki_dump/',
);

if ($deep) {
    push @rg_base, '--max-filesize', '100M';
}
else {
    push @rg_base, '-ttxt', '-tmd', '--max-filesize', '5M';
}

while (my $line = <STDIN>) {
    $line =~ s/[\r\n]+$//;
    next if $line =~ /^\s*$/;

    # Input format: TARGET whitespace ANCHOR TEXT
    # The anchor may contain spaces.
    my ($target, $anchor) = split /\s+/, $line, 2;
    next unless defined $target && defined $anchor && length $target && length $anchor;

    my $target_pattern = variant_regex($target);
    my @anchor_variants = variants($anchor);

    open my $rg, '-|', @rg_base, '-e', $target_pattern
        or die "Could not run rg: $!\n";

    while (my $hit = <$rg>) {
        next unless contains_any($hit, @anchor_variants);

        $hit = clean_line($hit) if $clean;
        print "$target\t$hit\n";

        last unless $all;
    }

    close $rg;
}

sub variants {
    my ($text) = @_;

    my $simp = opencc('t2s.json', $text);
    my $trad = opencc('s2t.json', $text);

    my %seen;
    return grep { !$seen{$_}++ } ($text, $simp, $trad);
}

sub variant_regex {
    my ($text) = @_;
    return join '|', map { quotemeta($_) } variants($text);
}

sub contains_any {
    my ($line, @needles) = @_;

    for my $needle (@needles) {
        return 1 if index($line, $needle) >= 0;
    }

    return 0;
}

sub clean_line {
    my ($line) = @_;

    $line =~ s/[\r\n]+$//;
    $line =~ s/^\[.*?\]\s*//;     # [146782006]
    $line =~ s/<[^>]+>//g;         # Unity/HTML-style tags
    $line =~ s/^[[:space:]]+//;
    $line =~ s/[[:space:]]+$//;

    return $line;
}

sub opencc {
    my ($config, $text) = @_;

    my $err = gensym;
    my $pid = open2(my $out, my $in, 'opencc', '-c', $config);

    print {$in} $text;
    close $in;

    local $/;
    my $converted = <$out> // '';
    close $out;
    waitpid($pid, 0);

    $converted =~ s/[\r\n]+$//;
    return $converted;
}

sub usage {
    print <<'USAGE';
Usage:
  printf 'TARGET ANCHOR\n' | miner.pl [options] [corpus ...]

Examples:
  printf '期颐 少年\n' | miner.pl -d
  printf '桡骨 右臂\n' | miner.pl ~/src/TurnBasedGameData/
  cat targets.txt | miner.pl --deep --all

Options:
  -d, --deep      Search Chinese Text Analysis plus HSR/Genshin dumps.
  -a, --all       Print all matching lines instead of first match only.
  --no-clean      Do not strip bracket IDs or formatting tags.
  -h, --help      Show this help.
USAGE
}
