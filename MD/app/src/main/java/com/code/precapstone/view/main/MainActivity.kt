package com.code.precapstone.view.main

import android.content.Intent
import androidx.appcompat.app.AppCompatActivity
import android.os.Bundle
import com.code.precapstone.R
import com.code.precapstone.databinding.ActivityMainBinding
import com.code.precapstone.view.category.CategoryActivity
import com.code.precapstone.view.setting.SettingsActivity

class MainActivity : AppCompatActivity() {
    private lateinit var binding: ActivityMainBinding
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        binding.ivSetting.setOnClickListener{
            val intent = Intent(this, SettingsActivity::class.java)
            startActivity(intent)
        }

        binding.fab.setOnClickListener{
            val intent = Intent(this, CategoryActivity::class.java)
            startActivity(intent)
        }

    }
}