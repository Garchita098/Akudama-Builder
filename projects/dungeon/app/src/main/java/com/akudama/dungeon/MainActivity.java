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
        root.setPadding(14,10,14,10);
        root.setFitsSystemWindows(true);
        root.setBackgroundColor(0xff0b111d);
        TextView title=new TextView(this);
        title.setText("LIVING DUNGEON  ·  0.3");
        title.setTextColor(0xffe1c393); title.setTextSize(21);
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
        stats.setText("Ход "+tick+"   ⚔ "+kills+"    Синие "+counts[0]+"  Алые "+counts[1]+"  Зелёные "+counts[2]+(paused?"   ПАУЗА":""));
        feed.setText(lastEvent);
        dungeon.invalidate();
    }
    class DungeonView extends View{
        final Paint p=new Paint();
        float zoom=1.15f,offsetX=0,offsetY=0,lastX,lastY; // movable dungeon camera
        DungeonView(){super(MainActivity.this);setBackgroundColor(0xff090d15);}
        void rect(Canvas c,float x,float y,float w,float h,int color){
            p.setColor(color);p.setStyle(Paint.Style.FILL);
            c.drawRect(x,y,x+w,y+h,p);
        }
        // Pixel-art warriors made from geometry, no external game engine required.
        void warrior(Canvas c,Unit u,float x,float y,float cs){
            c.save();c.translate(x,y);float q=cs/12f;c.scale(q,q);
            rect(c,2,10,8,2,0xff07090d);
            rect(c,3,3,6,7,0xff101219);
            rect(c,2,6,2,3,0xffc4aa79);rect(c,8,6,2,3,0xffc4aa79);
            rect(c,4,8,2,3,0xff343747);rect(c,7,8,2,3,0xff343747);
            int cloak=COLORS[u.team];
            rect(c,3,3,6,6,cloak);rect(c,4,4,4,4,0xff202937);
            rect(c,3,1,6,4,0xff252b35);rect(c,4,0,4,2,0xff8797a4);
            rect(c,4,3,4,1,0xff0a1018);
            rect(c,5,3,1,1,0xffe8caa2);rect(c,7,3,1,1,0xffe8caa2);
            rect(c,10,4,1,6,0xffaeb6b6);rect(c,10,3,2,2,0xffeff0e4);
            rect(c,1,6,2,4,0xff785c38);rect(c,1,7,2,1,0xffccae74);
            rect(c,1,12,10,1,0xff080b0f);
            c.restore();
        }
        @Override protected void onDraw(Canvas c){
            super.onDraw(c);
            float cell=Math.min(getWidth()/(float)W,getHeight()/(float)H)*zoom;
            float ox=(getWidth()-W*cell)/2f+offsetX,oy=(getHeight()-H*cell)/2f+offsetY;
            c.drawColor(0xff090d15);
            for(int x=0;x<W;x++)for(int y=0;y<H;y++){
                float px=ox+x*cell,py=oy+y*cell;
                int seed=(x*71+y*193+x*y*13)&255;
                if(wall[x][y]){
                    rect(c,px,py,cell,cell,0xff0c141d);
                    rect(c,px+1,py+1,cell-2,cell*.33f,0xff566376);
                    rect(c,px+1,py+cell*.34f,cell-2,cell*.62f,0xff293646);
                    rect(c,px+2,py+cell*.39f,cell*.46f,1,0xff131c2b);
                    rect(c,px+cell*.5f,py+cell*.67f,cell*.44f,1,0xff141c2b);
                    rect(c,px+2,py+cell*.77f,cell*.24f,1,0xff455364);
                }else{
                    rect(c,px,py,cell,cell,seed%3==0?0xff222834:0xff292d38);
                    rect(c,px+1,py+1,cell-2,cell-2,seed%4==0?0xff363844:0xff303440);
                    rect(c,px+cell*.5f,py+1,1,cell*.45f,0xff191f2a);
                    rect(c,px+1,py+cell*.52f,cell*.5f,1,0xff161c29);
                    if(seed%7==0)rect(c,px+cell*.22f,py+cell*.78f,cell*.24f,1,0xff68716c);
                    if(seed%23==0){
                        rect(c,px+cell*.33f,py+cell*.26f,cell*.33f,cell*.12f,0xff4b2626);
                    }
                }
            }
            for(Unit u:units){
                float px=ox+u.x*cell,py=oy+u.y*cell;
                warrior(c,u,px,py,cell);
                if(u.hp<4){
                    rect(c,px+2,py,cell-4,2,0xff431921);
                    rect(c,px+2,py,(cell-4)*u.hp/4f,2,0xffb5cf72);
                }
            }
        }
        @Override public boolean onTouchEvent(MotionEvent e){
            if(e.getAction()==MotionEvent.ACTION_DOWN){lastX=e.getX();lastY=e.getY();return true;}
            if(e.getAction()==MotionEvent.ACTION_MOVE){
                offsetX+=e.getX()-lastX;offsetY+=e.getY()-lastY;
                lastX=e.getX();lastY=e.getY();invalidate();return true;
            }
            return true;
        }
    }
}
