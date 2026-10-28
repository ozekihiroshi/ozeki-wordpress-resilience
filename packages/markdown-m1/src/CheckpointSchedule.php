<?php
declare(strict_types=1);
namespace OzekiResilience\M1;

final class CheckpointSchedule {
    public static function next(int $from,int $count,string $unit,\DateTimeZone $zone,int $anchorDay=0): int {
        if($count<1||$count>3650||!in_array($unit,['days','weeks','months'],true))throw new \RuntimeException('Invalid Checkpoint interval.');
        $d=(new \DateTimeImmutable('@'.$from))->setTimezone($zone);
        if($unit==='months'){
            $day=$anchorDay?:((int)$d->format('j'));
            $d=$d->modify('first day of this month')->modify('+'.$count.' months');
            $d=$d->setDate((int)$d->format('Y'),(int)$d->format('n'),min($day,(int)$d->format('t')));
        }else $d=$d->modify('+'.$count.' '.$unit);
        return $d->getTimestamp();
    }
}
