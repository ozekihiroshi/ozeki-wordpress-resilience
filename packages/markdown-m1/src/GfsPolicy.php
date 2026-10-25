<?php
declare(strict_types=1);
namespace Owr\M1;

/** Calendar scheduling and retention labels; contains no WordPress or storage effects. */
final class GfsPolicy {
    public static function normalize(array $input): array {
        $out=[];
        foreach(['weekly','monthly','yearly'] as $kind){
            $r=$input[$kind]??[];
            if(empty($r['enabled']))continue;
            $time=$r['time']??'';$keep=filter_var($r['keep']??null,FILTER_VALIDATE_INT);
            if(!is_string($time)||!preg_match('/^([01][0-9]|2[0-3]):[0-5][0-9]$/D',$time)||$keep===false||$keep<1||$keep>100)throw new \RuntimeException('Invalid GFS time or retention: '.$kind);
            $row=['enabled'=>true,'time'=>$time,'keep'=>$keep];
            foreach(($kind==='weekly'?['weekday'=>[0,6]]:($kind==='monthly'?['day'=>[0,31]]:['month'=>[1,12],'day'=>[1,31]])) as $key=>[$min,$max]){
                $v=filter_var($r[$key]??null,FILTER_VALIDATE_INT);
                if($v===false||$v<$min||$v>$max)throw new \RuntimeException('Invalid GFS '.$key.': '.$kind);
                $row[$key]=$v;
            }
            $out[$kind]=$row;
        }
        return $out;
    }
    public static function next(array $rules,int $after,\DateTimeZone $zone): ?array {
        $rules=self::normalize($rules);if(!$rules)return null;
        $start=(new \DateTimeImmutable('@'.$after))->setTimezone($zone)->setTime(0,0);
        $best=null;
        // Daily calendar iteration handles DST and leap years without fixed-second months.
        for($i=0;$i<=370;$i++){
            $date=$start->modify('+'.$i.' days');
            foreach($rules as $kind=>$r){
                $day=(int)$date->format('j');$last=(int)$date->format('t');
                $matches=match($kind){
                    'weekly'=>(int)$date->format('w')===$r['weekday'],
                    'monthly'=>$day===($r['day']===0?$last:min($r['day'],$last)),
                    'yearly'=>(int)$date->format('n')===$r['month']&&$day===min($r['day'],$last),
                };
                if(!$matches)continue;
                [$h,$m]=array_map('intval',explode(':',$r['time']));$at=$date->setTime($h,$m)->getTimestamp();
                if($at<=$after)continue;
                if($best===null||$at<$best['at'])$best=['at'=>$at,'timezone'=>$zone->getName(),'rules'=>[$kind=>$r]];
                elseif($at===$best['at'])$best['rules'][$kind]=$r;
            }
            if($best!==null)return $best;
        }
        throw new \RuntimeException('Cannot find next GFS occurrence.');
    }
    public static function labels(array $rules,int $confirmed,\DateTimeZone $zone): array {
        $out=[];$d=(new \DateTimeImmutable('@'.$confirmed))->setTimezone($zone);
        foreach(self::normalize($rules) as $kind=>$r){
            if($kind==='weekly')$end=$d->modify('+'.$r['keep'].' weeks');
            else{
                $months=$r['keep']*($kind==='yearly'?12:1);
                $end=$d->modify('first day of this month')->modify('+'.$months.' months');
                $end=$end->setDate((int)$end->format('Y'),(int)$end->format('n'),min((int)$d->format('j'),(int)$end->format('t')));
            }
            $out[$kind]=['keep'=>$r['keep'],'expires_at'=>$end->format('c')];
        }return $out;
    }
    public static function active(array $labels,int $now): bool {
        $active=false;
        foreach($labels as $kind=>$label){
            if(!in_array($kind,['weekly','monthly','yearly'],true)||!is_array($label)||!is_string($label['expires_at']??null)||($until=strtotime($label['expires_at']))===false)throw new \RuntimeException('Invalid GFS retention label; deletion stopped.');
            if($until>$now)$active=true;
        }return $active;
    }
}
