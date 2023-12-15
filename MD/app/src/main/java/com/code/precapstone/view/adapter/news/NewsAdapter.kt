package com.code.precapstone.view.adapter.news

import android.content.Intent
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView
import com.code.precapstone.R
import com.code.precapstone.data.model.DataNews
import com.code.precapstone.view.articles.ArticlesActivity

class NewsAdapter(private val newsList: List<DataNews>) :
    RecyclerView.Adapter<NewsAdapter.NewsViewHolder>() {

    class NewsViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
        val judulTextView: TextView = itemView.findViewById(R.id.tvJudulBerita)
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): NewsViewHolder {
        val itemView = LayoutInflater.from(parent.context).inflate(R.layout.item_news_row, parent, false)
        return NewsViewHolder(itemView)
    }

    override fun onBindViewHolder(holder: NewsViewHolder, position: Int) {
        val currentItem = newsList[position]
        holder.judulTextView.text = currentItem.judul
        holder.itemView.setOnClickListener{
            val intent = Intent(holder.itemView.context, ArticlesActivity::class.java)
            intent.putExtra("url", currentItem.link)
            holder.itemView.context.startActivity(intent)
        }
    }

    override fun getItemCount() = newsList.size
}
