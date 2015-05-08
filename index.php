<?php
ini_set( 'display_errors', 'Off' );
error_reporting( E_ALL );
$recipe['piston']='planks:3,cobblestone:4,iron:1,redstone:1';
$recipe['sticky_piston']='piston:1,slime_ball:1';
$recipe['planks']='wood:0.25';
$recipe['rail']='iron:0.375,stick:0.0625';
$recipe['detector_rail']='iron:1,redstone:0.1667,stone_preassure_plate:0.1667';
$recipe['activator_rail']='iron:1,stick:0.3333,redstone_torch:0.1667';
$recipe['powered_rail']='gold:1,stick:0.1667,redstone:0.1667';
$recipe['redstone_torch']='stick:1,redstone:1';
$recipe['redstone_lamp']='redstone:4,glowstone:1';
$recipe['stone_preassure_plate']='stone:2';
$recipe['hopper']='iron:5,chest:1';
$recipe['daylight_sensor']='quartz:3,glass:3,plank_slab:3';
$recipe['minecart']='iron:5';
$recipe['bookshelf']='planks:6,book:3';
$recipe['beacon']='obsidian:3,glass:5,nether_star:1';
$recipe['book']='paper:3,leather:1';
$recipe['paper']='sugar_cane:1';
$recipe['chest']='planks:8';
$recipe['stick']='planks:0.5';
$recipe['glass']='sand:1,coal:0.125';
$recipe['plank_slab']='planks:0.5';
$recipe['stone_bricks']='stone:1';
$recipe['wood_stairs']='planks:1.5';
$recipe['quartz_stairs']='quartz_block:1.5';
$recipe['bricks_stairs']='bricks:1.5';
$recipe['emerald_block']='emerald:9';
$recipe['quartz_block']='quartz:4';
$recipe['enchantment_table']='obsidian:4,diamond:2,book:1';
$recipe['ladder']='stick:2.3333';
$recipe['sign']='planks:2,stick:0.3333';
$recipe['torch']='stick:0.25,coal:0.25';
$recipe['fence']='stick:0.6667,planks:1.3333';
$recipe['anvil']='iron:4,iron_block:3';
$recipe['iron_block']='iron:9';
$recipe['corase_dirt']='dirt:0.5,gravel:0.5';
$recipe['sandstone']='sand:4';
$recipe['sandstone_stairs']='sandstone:1.5';
$recipe['stone_brick_stairs']='stone_bricks:1.5';
$recipe['nether_bricks_stairs']='nether_bricks:1.5';
$recipe['stone_brick_slab']='stone_bricks:0.5';
$recipe['quartz_slab']='quartz_block:0.5';
$recipe['sandstone_slab']='sandstone:0.5';
$recipe['cobblestone_slab']='cobblestone:0.5';
$recipe['bricks_slab']='bricks:0.5';
$recipe['stone_slab']='stone:0.5';
$recipe['nether_bricks_slab']='nether_bricks:0.5';
$recipe['iron_block']='iron:9';
$recipe['diamond_block']='diamond:9';
$recipe['gold_block']='gold:9';
$recipe['redstone_block']='redstone:9';
$recipe['slime_block']='slime_ball:9';
$recipe['chiseled_stone_bricks']='stone_brick_slab:2';
$recipe['chiseled_quartz_block']='quartz_slab:2';
$recipe['quartz_pillar']='quartz_block:1';
$recipe['note_block']='planks:8,redstone:1';
$recipe['lapis_block']='lapis:9';
$recipe['coal_block']='coal:9';
$recipe['armor_stand']='stick:6,stone_slab:1';
$recipe['bed']='wool:3,planks:3';
$recipe['fence_gate']='stick:4,planks:2';
$recipe['wooden_trapdoor']='planks:3';
$recipe['redstone_repeater']='stone:3,redstone:1,redstone_torch:2';
$recipe['redstone_comparator']='stone:3,redstone_torch:3,quartz:1';
$recipe['dispenser']='cobblestone:7,redstone:1,bow:1';
$recipe['dropper']='cobblestone:7,redstone:1';
$recipe['bow']='stick:3,string:3';
$recipe['item_frame']='stick:8,leather:1';
$recipe['painting']='stick:8,wool:1';
$recipe['potion_fire_resist_8']='glass:1,nether_wart:0.3333,magma_cream:0.3333,redstone:0.3333';
$recipe['magma_cream']='slime_ball:1,blaze_powder:1';
$recipe['blaze_powder']='blaze_rod:0.5';
$recipe['iron_trapdoor']='iron:4';
$recipe['iron_door']='iron:2';
$recipe['wooden_door']='planks:2';
$recipe['jukebox']='planks:8,diamond:1';
$recipe['bricks']='brick:4';
$recipe['brick']='clay_ball:1,coal:0.125';
$recipe['boat']='planks:5';
$recipe['nether_bricks']='nether_brick:4';
$recipe['nether_brick']='netherrack:1,coal:0.125';
$recipe['arrow']='flint:0.25,stick:0.25,feather:0.25';
$recipe['bow']='stick:3,string:3';
$recipe['iron']='end';
$recipe['redstone']='end';
$recipe['wood']='end';
$recipe['cobblestone']='end';
$recipe['slime_ball']='end';
$recipe['gold']='end';
$recipe['quartz']='end';
$recipe['sand']='end';
$recipe['coal']='end';
$recipe['glowstone']='end';
$recipe['stone']='end';
$recipe['sugar_cane']='end';
$recipe['leather']='end';
$recipe['nether_star']='end';
$recipe['obsidian']='end';
$recipe['emerald']='end';
$recipe['diamond']='end';
$recipe['dirt']='end';
$recipe['gravel']='end';
$recipe['wool']='end';
$recipe['lapis']='end';
$recipe['clay_ball']='end';
$recipe['string']='end';
$recipe['nether_wart']='end';
$recipe['blaze_rod']='end';
$recipe['netherrack']='end';
$recipe['flint']='end';
$recipe['feather']='end';

function craft($item,$qty){
	global $recipe;
	$items=Array();
	$itemsq=Array();
	$nitems=Array();
	$nitemsq=Array();
	$items[0]=$item;
	$itemsq[0]=$qty;
	do{
		$allend=0;
		foreach($items as $k=>$v){
			if($recipe[$v]!='end'){
				$allend+=1;
				$tmp=explode(',',$recipe[$v]);
				foreach($tmp as $t){
					$t2=explode(':',$t);
					$nitems[count($nitems)]=$t2[0];
					$nitemsq[count($nitemsq)]=($t2[1]*$itemsq[$k]);
				}
			}
			else{
				$nitems[count($nitems)]=$v;
				$nitemsq[count($nitemsq)]=$itemsq[$k];
			}
		}
		$items=$nitems;
		$itemsq=$nitemsq;
		$nitems=Array();
		$nitemsq=Array();
	}while($allend!=0);
	foreach($items as $key=>$val){
		$re[$val]=$itemsq[$key];
	}
	return $re;
}

echo('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
	"http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
<head>
	<title>MC crafting materials checker</title>
	<meta http-equiv="content-type" content="text/html;charset=utf-8" />
	<meta name="generator" content="Geany 1.22" />
	<link rel="stylesheet" type="text/css" href="style.css" />
	<script src="script.js" language="javascript"></script>
</head><body>');
echo('<div class="main"><table border="0" width="100%"><tr width="100%"><td width="50%">');
echo('<form name="things" action="index.php" method="POST"><p>Select items</p>');
for($i=1;$i<=8;$i+=1) echo('<span id="f'.$i.'" style="display: none;"><img id="f'.$i.'img" src="#" width="64" height="64"><input type="hidden" name="f'.$i.'h" value="" id="f'.$i.'hi"><input id="f'.$i.'f" name="f'.$i.'f" type="text" class="formfld" size="3" maxlength="4"><a href="#" onclick="hideLine(parentNode.id)"><img src="gfx/x.png" id="x"></a></span>');
echo('</td><td width="50%">');
$itemsToCraft=Array('piston','sticky_piston','hopper','daylight_sensor','redstone_lamp','redstone_repeater','redstone_comparator','redstone_torch','dispenser','dropper','iron_trapdoor','iron_door','jukebox','rail','powered_rail','activator_rail','detector_rail','minecart','bookshelf','beacon',
'cobblestone_slab','stone_bricks','stone_brick_stairs','stone_brick_slab','chiseled_stone_bricks','planks','wood_stairs','plank_slab','bricks','bricks_stairs','bricks_slab','emerald_block','diamond_block','gold_block',
'iron_block','redstone_block','slime_block','lapis_block','coal_block','quartz_block','quartz_stairs','quartz_slab','chiseled_quartz_block','quartz_pillar','anvil','enchantment_table','ladder','sign','fence','fence_gate','boat','wooden_trapdoor','wooden_door','chest',
'torch','corase_dirt','sandstone','sandstone_stairs','sandstone_slab','note_block','bed','armor_stand','item_frame','painting','arrow','nether_bricks','nether_bricks_stairs','nether_bricks_slab');
foreach($itemsToCraft as $it){
	echo('<a href="#" title="'.ucwords(str_replace('_',' ',$it)).'" id="'.$it.'" onclick="addItem(this.id)" style="vertical-align:top;"><img src="gfx/'.$it.'.png" width="64" height="64" border="0" alt="'.ucwords(str_replace('_',' ',$it)).'" id="'.$it.'"></a>');
}
echo('</td></tr><tr><td colspan="2"><input type="submit" name="submit" value="Go!" class="formbtn" id="gobtn" onmouseover="btnh(this.id)" onmouseout="btnd(this.id)"></form></td></tr></table>');
if(isset($_POST['submit'])){
	$stck=Array('blaze_rod'=>64,'coal'=>64,'cobblestone'=>64,'diamond'=>64,'dirt'=>64,'emerald'=>64,'feather'=>64,'gold'=>64,'lapis'=>64,'leather'=>64,'iron'=>64,'nether_star'=>64,'nether_wart'=>64,'netherrack'=>64,'obsidian'=>64,'quartz'=>64,'redstone'=>64,'sand'=>64,'slime_ball'=>64,'stone'=>64,'string'=>64,'sugar_cane'=>64,'wood'=>64,'wool'=>64,
	'clay_ball'=>16,'ender_pearl'=>16,'egg'=>16,'armor_stand'=>16,'sign'=>16,
	'bow'=>1,'bed'=>1);
	echo('</div><div class="main2">');
	$ra=Array();
	for($j=1;$j<=8;$j+=1){ // 8 input slots
		if(strlen($_POST['f'.$j.'h'])>2){ //if isset
			$ta=craft($_POST['f'.$j.'h'],$_POST['f'.$j.'f']); //actually check the recipe
			foreach($ta as $taik=>$tai){ //for each item in the recipe
				$ra[$taik]+=$tai; //add to the results array
			}
		}
	}
	echo('<p>You will need:</p>');
	foreach($ra as $ak=>$av){
		echo('<p><img title="'.ucwords(str_replace('_',' ',$ak)).'" src="gfx/'.$ak.'.png"> x ');
		if(($av-floor($av))==0) echo $av;
		else echo((floor($av)+1));
		if($av>64) echo(' ('.round($av/$stck[$ak],2).' stacks)'); //stacks
		if(round($av/$stck[$ak],2)>54) echo(' ['.round(($av/$stck[$ak])/54,2).' double chests]'); //double chests
		echo('</p>');
	}
}
echo('</div></body></html>');
?>
