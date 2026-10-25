<?php
declare(strict_types=1);
namespace Owr\M1;

/** Diagnostic only: never a recovery payload, confirmation or retry queue. */
final class SaveFailure
{
    public const OPTION='owr_m1_capture_error';
    public static function run(string $context,callable $operation): mixed {
        try { return $operation(); }
        catch (\Throwable $error) {
            $record=['at'=>gmdate('c'),'context'=>$context,'reason'=>$error->getMessage()];
            try {
                update_option(self::OPTION,$record,false);
                if(get_option(self::OPTION)!==$record)error_log('Resilience: capture failure diagnostic could not be persisted.');
            } catch (\Throwable $loggingError) {
                error_log('Resilience: capture failure diagnostic could not be persisted.');
            }
            // Keep the original failure behaviour. Never continue or certify here.
            throw $error;
        }
    }
}
