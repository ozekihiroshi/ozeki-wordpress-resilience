<?php
declare(strict_types=1);
namespace OzekiResilience\M1;
if (!defined('ABSPATH')) exit;

/** Own only a unique child directory; never remove caller-owned parent data. */
// phpcs:disable WordPress.WP.AlternativeFunctions -- Private local staging requires OS permissions, file locks and checked deletion results. WP_Filesystem remote transports cannot supply these guarantees; this class never handles plugin installation files.
final class RecoveryWorkspace {
    private string $directory;
    private string $token;
    private bool $retained=false;
    private $ownerHandle;
    public function __construct(string $parent) {
        $root=realpath($parent);$web=realpath(ABSPATH);
        if($root===false||!is_dir($root)||!is_writable($root)||is_link($parent)||($web!==false&&($root===$web||str_starts_with($root,$web.DIRECTORY_SEPARATOR))))throw new \RuntimeException('Private writable staging directory outside web root required.');
        $this->token=bin2hex(random_bytes(16));$this->directory=$root.'/owr-recovery-'.$this->token;
        if(!mkdir($this->directory,0700))throw new \RuntimeException('Cannot create private recovery workspace.');
        try {
            if(file_put_contents($this->directory.'/.owner',$this->token)!==strlen($this->token))throw new \RuntimeException('Cannot mark recovery workspace ownership.');
            $this->ownerHandle=fopen($this->directory.'/.owner','r+');
            if(!$this->ownerHandle||!flock($this->ownerHandle,LOCK_EX|LOCK_NB))throw new \RuntimeException('Cannot lock recovery workspace.');
        } catch(\Throwable $e) {
            if(is_resource($this->ownerHandle))fclose($this->ownerHandle);
            // No recovery has begun. Only the marker in our newly created directory exists.
            if(is_file($this->directory.'/.owner'))unlink($this->directory.'/.owner');
            rmdir($this->directory);
            throw $e;
        }
    }
    public function path(): string {return $this->directory;}
    public static function writeBackup(string $directory,string $name,string $contents): void {
        if(!in_array($name,['before-content.json','before-files.json','before-options.json'],true)||is_link($directory)||!is_dir($directory))throw new \RuntimeException('Invalid recovery backup path.');
        $path=$directory.'/'.$name;
        if(is_link($path))throw new \RuntimeException('Recovery backup must not be a symbolic link.');
        if(file_put_contents($path,$contents)!==strlen($contents)||!chmod($path,0600))throw new \RuntimeException('Cannot complete private recovery backup; recovery stopped before content replacement.');
    }
    public function retain(): void {$this->retained=true;}
    public static function unfinished(string $parent): array {
        $out=[];
        foreach(glob(rtrim($parent,'/').'/owr-recovery-*',GLOB_ONLYDIR)?:[] as $dir){
            if(is_link($dir)||!preg_match('/^owr-recovery-([a-f0-9]{32})$/D',basename($dir),$m)||is_link($dir.'/.owner'))continue;
            $h=@fopen($dir.'/.owner','r+');if(!$h)continue;
            if(trim(stream_get_contents($h))===$m[1]&&flock($h,LOCK_EX|LOCK_NB)){$out[]=$dir;flock($h,LOCK_UN);}
            fclose($h);
        }
        return $out;
    }
    public function finish(): void {
        if($this->retained||!is_dir($this->directory))return;
        if(is_link($this->directory)||@file_get_contents($this->directory.'/.owner')!==$this->token)throw new \RuntimeException('Recovery workspace ownership changed; cleanup stopped.');
        // Only known files created by this operation. Unexpected files are never erased.
        foreach(['before-content.json','before-files.json','before-options.json'] as $file){$p=$this->directory.'/'.$file;if(is_link($p))throw new \RuntimeException('Recovery workspace contains a symbolic link.');if(is_file($p)&&!unlink($p))throw new \RuntimeException('Recovery workspace cleanup incomplete.');}
        $left=array_diff(scandir($this->directory),['.','..','.owner']);
        if($left)throw new \RuntimeException('Recovery workspace contains unexpected files; cleanup incomplete.');
        if(!unlink($this->directory.'/.owner')||!rmdir($this->directory))throw new \RuntimeException('Recovery workspace cleanup incomplete.');
        if(is_resource($this->ownerHandle)){flock($this->ownerHandle,LOCK_UN);fclose($this->ownerHandle);}
    }
}

/** Retain rollback evidence if restoring the previous state could not finish. */
final class RecoveryRollbackIncomplete extends \RuntimeException {}
