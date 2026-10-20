package com.akudama.dungeon;

import android.app.Activity;
import android.os.Bundle;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.Color;
import android.view.View;
import android.view.MotionEvent;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Button;
import java.util.ArrayList;
import java.util.Random;

public class MainActivity extends Activity {
    final Random rng=new Random();
    final int W=24,H=32,COUNT=38;
    final int[] COLORS={0xff52b4ef,0xffff766d,0xffa9dd83};
    final String[] NAMES={"Синие","Алые","Зелёные"};
    boolean[][] wall=new boolean[W][H];
    ArrayList<Unit> units=new ArrayList<>();
    TextView stats,feed;
    DungeonView dungeon;
    boolean paused=false;
    int tick=0,kills=0;
    String lastEvent="Мир пробуждается…";
    static class Unit {
        int x,y,team,hp=4;
        Unit(int x,int y,int team){this.x=x;this.y=y;this.team=team;}
    }
    @Override public void onCreate(Bundle state){
        super.onCreate(state);
        LinearLayout root=new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(14,16,14,10);
        root.setBackgroundColor(0xff0b111d);
        TextView title=new TextView(this);
        title.setText("LIVING DUNGEON  ·  0.2");
        title.setTextColor(Color.WHITE); title.setTextSize(23);
        root.addView(title);
        stats=new TextView(this); stats.setTextColor(0xffacd3ea);stats.setTextSize(14);
        root.addView(stats);
        dungeon=new DungeonView();
        root.addView(dungeon,new LinearLayout.LayoutParams(-1,0,1));
        feed=new TextView(this);feed.setTextColor(0xffffd59b);feed.setTextSize(14);
        feed.setPadding(0,8,0,8);root.addView(feed);
        LinearLayout controls=new LinearLayout(this);
        Button pause=new Button(this);pause.setText("Пауза");
        pause.setOnClickListener(v->{paused=!paused;pause.setText(paused?"Продолжить":"Пауза");updateUi();});
        controls.addView(pause,new LinearLayout.LayoutParams(0,-2,1));
        Button reset=new Button(this);reset.setText("Новый мир");
        reset.setOnClickListener(v->{generate();updateUi();});
        controls.addView(reset,new LinearLayout.LayoutParams(0,-2,1));
        root.addView(controls);
        setContentView(root);
        generate();updateUi();
        dungeon.postDelayed(new Runnable(){
            @Override public void run(){
                if(!paused){step();updateUi();}
                dungeon.postDelayed(this,450);
            }
        },450);
    }
    void generate(){
        tick=0;kills=0;units.clear();
        for(int x=0;x<W;x++)for(int y=0;y<H;y++){
            wall[x][y]=x==0||y==0||x==W-1||y==H-1||rng.nextDouble()<0.16;
        }
        for(int i=0;i<COUNT;i++){
            for(int tries=0;tries<500;tries++){
                int x=1+rng.nextInt(W-2),y=1+rng.nextInt(H-2);
                if(!wall[x][y]&&!occupied(x,y)){units.add(new Unit(x,y,i%3));break;}
            }
        }
        lastEvent="В подземелье появились три фракции.";
    }
    boolean occupied(int x,int y){
        for(Unit u:units)if(u.hp>0&&u.x==x&&u.y==y)return true;
        return false;
    }
    Unit at(int x,int y){
        for(Unit u:units)if(u.hp>0&&u.x==x&&u.y==y)return u;
        return null;
    }
    void step(){
        tick++;
        ArrayList<Unit> order=new ArrayList<>(units);
        java.util.Collections.shuffle(order,rng);
        for(Unit u:order){
            if(u.hp<=0)continue;
            Unit nearest=null;int distance=9999;
            for(Unit v:units){
                if(v.hp<=0||v.team==u.team)continue;
                int d=Math.abs(v.x-u.x)+Math.abs(v.y-u.y);
                if(d<distance){distance=d;nearest=v;}
            }
            if(nearest==null)continue;
            if(distance==1){
                nearest.hp--;
                if(nearest.hp<=0){
                    kills++;
                    lastEvent=NAMES[u.team]+" победили бойца фракции «"+NAMES[nearest.team]+"»";
                }
            }else{
                int dx=0,dy=0;
                if(distance<10){
                    if(Math.abs(nearest.x-u.x)>Math.abs(nearest.y-u.y))dx=Integer.compare(nearest.x,u.x);
                    else dy=Integer.compare(nearest.y,u.y);
                }else{
                    int n=rng.nextInt(4);
                    dx=n==0?1:n==1?-1:0;
                    dy=n==2?1:n==3?-1:0;
                }
                if(canMove(u.x+dx,u.y+dy)){u.x+=dx;u.y+=dy;}
                else {
                    int n=rng.nextInt(4),rx=n==0?1:n==1?-1:0,ry=n==2?1:n==3?-1:0;
                    if(canMove(u.x+rx,u.y+ry)){u.x+=rx;u.y+=ry;}
                }
            }
        }
        units.removeIf(u->u.hp<=0);
        if(tick%24==0){
            for(int team=0;team<3;team++){
                int count=0;for(Unit u:units)if(u.team==team)count++;
                if(count>0&&count<18){
                    for(int tries=0;tries<30;tries++){
                        Unit parent=units.get(rng.nextInt(units.size()));
                        if(parent.team!=team)continue;
                        int nx=parent.x+rng.nextInt(3)-1,ny=parent.y+rng.nextInt(3)-1;
                        if(canMove(nx,ny)){units.add(new Unit(nx,ny,team));break;}
                    }
                }
            }
        }
        if(units.size()<=1)lastEvent="Подземелье почти опустело. Нажми «Новый мир».";
    }
    boolean canMove(int x,int y){return x>=1&&x<W-1&&y>=1&&y<H-1&&!wall[x][y]&&!occupied(x,y);}
    void updateUi(){
        int[] counts=new int[3];
        for(Unit u:units)counts[u.team]++;
        stats.setText("Ход "+tick+"   ⚔ "+kills+"   ● "+counts[0]+"   ● "+counts[1]+"   ● "+counts[2]+(paused?"   ПАУЗА":""));
        feed.setText(lastEvent);
        dungeon.invalidate();
    }
    class DungeonView extends View{
        Paint p=new Paint(3);
        DungeonView(){super(MainActivity.this);setBackgroundColor(0xff0c1524);}
        @Override protected void onDraw(Canvas c){
            super.onDraw(c);
            float cell=Math.min(getWidth()/(float)W,getHeight()/(float)H);
            float ox=(getWidth()-W*cell)/2f,oy=(getHeight()-H*cell)/2f;
            for(int x=0;x<W;x++)for(int y=0;y<H;y++){
                p.setColor(wall[x][y]?0xff26374b:((x+y)%2==0?0xff111f2f:0xff152638));
                c.drawRect(ox+x*cell,oy+y*cell,ox+(x+1)*cell+0.2f,oy+(y+1)*cell+0.2f,p);
            }
            for(Unit u:units){
                p.setColor(COLORS[u.team]);
                c.drawCircle(ox+(u.x+0.5f)*cell,oy+(u.y+0.5f)*cell,cell*0.38f,p);
                p.setColor(0xff17202b);
                c.drawCircle(ox+(u.x+0.5f)*cell,oy+(u.y+0.5f)*cell,cell*0.13f,p);
            }
        }
    }
}
